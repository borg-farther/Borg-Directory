# Decision: semantic retrieval stays an opt-in extra (not the default) for the pilot

Status: **decided** (2026-06-14, pre-pilot hardening pass). Revisit after the
pilot if the day-15 decision is BUILD.

## Question

The verdict flagged that the default matcher is **lexical, not semantic**, and
that low conversational recall (issue #9) can make the activation gate misread a
good product as "no value." Should we make semantic retrieval the **default
install** so a fresh `pip install agent-borg` does meaning-based matching out of
the box?

## What we measured (reproducible: `scripts/`-free, plain pip)

Measured on this box, Python 3.12, 2026-06-14. The `[semantic]` extra is
`sentence-transformers>=2.2.0, numpy>=1.24.0, scikit-learn>=1.3.0`.

| Dimension | Base (`agent-borg`) | With `[semantic]` |
|---|---|---|
| Wheel / download footprint | **580 KB** wheel | **2.7 GB** download (59 wheels: torch 532 MB + CUDA/nvidia stack + transformers) |
| Installed size | a few MB | **5.1 GB** site-packages |
| Install wall time | seconds | **87 s** from a warm local cache (excludes the multi-minute first download) |
| Cold import | negligible | **6.7 s** just to `import sentence_transformers` |
| First model use | none | **downloads ~90 MB from HuggingFace over the network** (e.g. `all-MiniLM-L6-v2`) |
| Offline-first | yes ($0, no network) | **no** — first semantic query needs network to fetch the model |

## Decision: NO. Keep semantic an explicit `[semantic]` extra.

Reasons, in order:

1. **It breaks the product's core promises.** Borg's pitch and its measured
   day-one value are *tiny, offline, $0, ~11 s time-to-value* (E-011). A default
   that adds 2.7 GB of download, ~5.1 GB on disk, ~87 s of install, and a
   **network round-trip to HuggingFace on first use** destroys exactly the
   properties the cold-smoke gate verifies. The 11 s TTV becomes minutes.

2. **It would not even fix the rescue matcher by itself.** The miss in issue #9
   is in `rescue()` → `borg.core.pack_taxonomy.classify_error`, which is a
   substring/keyword classifier, *not* the `borg search` path. Embeddings only
   help retrieval (`borg_search` mode=`semantic`); making the **rescue
   classifier** semantic is a separate, larger change (route classification
   through similarity against the seed corpus). So paying the 5.1 GB cost would
   buy better `borg search` but still leave the activation-critical
   `borg rescue` conversational miss largely in place.

3. **The cost/benefit is wrong for a 10-user pilot** whose recruits already use
   Python/Django/Docker daily and mostly have a literal error in hand.

## What we did instead (this PR)

- **Conversational-miss detection** in `borg.core.rescue` (`_looks_conversational`,
  `_conversational_miss_extras`). When a likely-conversational input misses, the
  rescue stays `no_confident_match` (never fabricates) but **stops being a silent
  zero**: it tells the user Borg matches the literal error signature, and when a
  module is named in the prose ("can't find a module called django") it hands
  them the exact command that *does* match:
  `borg rescue "ModuleNotFoundError: No module named 'django'"`. Deterministic,
  zero new dependencies, offline. Tests: `tests/core/test_conversational_miss.py`.
- **Reproducible recall measurement** (`eval/recall_harness.py`, CI-gated by
  `tests/readiness/test_recall_harness.py`) so the conversational gap is a
  tracked number (literal 0.83 vs conversational 0.14, precision 1.00), not prose.

## Revisit criteria (post-pilot)

If day-15 is BUILD, evaluate a **small CPU-only embedding path** (e.g. a quantized
MiniLM via `onnxruntime`, model vendored or fetched once with explicit consent)
that preserves offline-first, AND wire semantic similarity into the rescue
classifier — not just `borg search`. Re-run `eval/recall_harness.py` to prove the
conversational number actually moves before shipping it on by default.

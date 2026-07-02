# Minimum Capable Agent Stack

Borg helps most when the host agent is already competent. This packet defines the minimum free/local stack: capable model, structured outputs, local retrieval, durable memory, real tools, a tight prompt, and a fixed eval loop.

## Implementation order

1. **Capable base model** (`capable_base_model`)
2. **Structured outputs** (`structured_outputs`)
3. **Real tools, not just chat** (`real_tools`)
4. **Tight system prompt** (`tight_system_prompt`)
5. **Persistent memory** (`persistent_memory`)
6. **RAG over your own docs** (`rag_layer`)
7. **Eval loop** (`eval_loop`)

## The seven levers

### Capable base model

Model quality is the biggest single lever. A weak default model wastes every downstream improvement.

Minimum free/local path:
- Use the most capable currently-free open model your host can reach; OpenRouter free-tier open models are a common path.
- Pin one known-good default model for the main task instead of floating on 'latest free'.
- Keep a cheaper fallback model only for background or non-critical work.

Done when:
- The host has one pinned default reasoning model that is clearly stronger than the weakest available default.
- Model changes are tracked in the eval log instead of being swapped ad hoc.

Proof:
- Host config records provider + exact model id.
- A fixed eval set is rerun before/after any model switch.

Anti-patterns:
- Shipping on the weakest base model because it is free.
- Floating model ids across eval runs.
- Treating retrieval or prompting as a substitute for insufficient model capability.

### Structured outputs

JSON-schema output contracts sharply reduce hallucinated tool calls, broken parsing, and glue-code drift.

Minimum free/local path:
- Use native JSON-schema or schema-constrained output mode whenever the host/provider supports it.
- Validate the model response against the schema before using it.
- Fail closed when validation fails; do not silently coerce malformed output into tool arguments.

Done when:
- Tool-selection and machine-readable answers flow through an explicit schema.
- Malformed outputs are visible in tests and logs instead of being silently repaired.

Proof:
- Eval cases include at least one exact-schema response and one invalid-schema negative control.
- Tool argument payloads are validated before execution.

Anti-patterns:
- Free-form prose that downstream code regex-parses.
- Best-effort parsing that hides model failures.
- Letting the model invent tool names or argument shapes.

### RAG over your own docs

Even a small local knowledge base beats guessing from stale priors when the answer already exists in your docs, specs, or runbooks.

Minimum free/local path:
- Index operator docs, runbooks, API references, and project conventions into a local vector store.
- Chroma or Qdrant local mode is sufficient for a first pass.
- Retrieve the smallest relevant chunks and cite the source path/section in the answer.

Done when:
- The agent can answer doc-backed questions from local material instead of memory alone.
- Retrieved snippets carry source metadata the operator can inspect.

Proof:
- Eval cases include questions whose answers appear only in local docs.
- The answer includes retrieval provenance instead of unsupported certainty.

Anti-patterns:
- Indexing nothing and calling it RAG.
- Dumping huge irrelevant contexts into the prompt.
- Claiming retrieval helped without citing the retrieved source.

### Persistent memory

An agent that forgets user preferences, corrections, and prior decisions every turn barely compounds.

Minimum free/local path:
- Persist durable user preferences, recurring corrections, and stable project conventions in SQLite or an equivalent local store.
- Differentiate durable memory from ephemeral conversation history.
- Load only compact, still-relevant facts into the prompt.

Done when:
- The agent remembers stable user and project facts across sessions.
- Temporary task state is not confused with durable memory.

Proof:
- A repeated user preference persists across a fresh session.
- An eval case checks that a prior correction is applied without re-teaching.

Anti-patterns:
- Stateless sessions for every turn.
- Stuffing the entire conversation transcript into memory.
- Saving stale execution logs or temporary TODOs as long-term facts.

### Real tools, not just chat

Without tools, the agent cannot ground itself against the real world and becomes a chatbot wearing an operator costume.

Minimum free/local path:
- Expose file read/write, code execution, and web lookup at minimum.
- Use explicit tool schemas and verify tool arguments before execution.
- Require the agent to use tools for current facts instead of guessing.

Done when:
- The host can inspect files, run verification commands, and fetch missing facts.
- Tool use is available in both happy-path and evaluation flows.

Proof:
- Eval cases require a web/file/tool action the model cannot solve from priors alone.
- Tool-call transcripts show grounded evidence, not imaginary tool results.

Anti-patterns:
- Calling the system an agent when it cannot act.
- Inventing tool outputs when calls fail.
- Disabling tools in evals and still claiming production readiness.

### Tight system prompt

Clear role, constraints, output shape, and failure behavior fix more bugs than most libraries.

Minimum free/local path:
- State the agent role, operating boundaries, response format, and failure modes explicitly.
- Tell the agent when to say 'I don't know', when to call tools, and when to verify before answering.
- Keep the prompt small enough that the important rules are not buried.

Done when:
- The prompt defines tool-use expectations, schema expectations, and fail-closed behavior.
- The operator can point to one canonical prompt source of truth.

Proof:
- Eval cases include negative controls for guessing instead of tool use.
- Prompt changes are versioned and rerun through the same eval set.

Anti-patterns:
- Vague 'helpful assistant' prompts for agent workflows.
- Prompt bloat that hides the few rules that matter.
- Changing prompt text without rerunning evals.

### Eval loop

Without a fixed eval set, every tweak is vibes. With one, you can tell whether a change helped, regressed, or only moved style around.

Minimum free/local path:
- Keep a small fixed set of real operator questions, failures, and tool-use tasks.
- Promptfoo is a fine local harness when available, but any repeatable local scorer is acceptable.
- Rerun the same eval set for model, prompt, tool, memory, or RAG changes before shipping.

Done when:
- Every meaningful host change has before/after eval evidence.
- Regression cases are added when the agent fails in production or dogfood.

Proof:
- Eval results are logged per model/prompt/tool configuration.
- Shipping is blocked when the fixed eval set regresses on grounded tasks.

Anti-patterns:
- Shipping based on anecdotal one-off wins.
- Changing multiple variables at once and calling the outcome causal.
- No regression suite for previously-seen failures.

## Eval contract

Do not ship a model/prompt/tool/memory/RAG change until the same fixed eval set has been rerun and reviewed.

Taskset: `eval/tasksets/minimum_capable_agent_stack.json`

- Can the host emit exact schema-valid JSON for a tool-selection or structured-answer task?
- Does it call tools instead of guessing when current facts or files are required?
- Can it answer a question that only exists in local docs via retrieval with provenance?
- Does it remember a prior user preference or correction in a fresh session?
- Does it say NO_CONFIDENT_MATCH / insufficient context instead of faking certainty when evidence is absent?

## Commands

- Inspect: `borg agent-stack --json`
- First-user contract: `borg first-10 --json`
- Host priming: `borg agent-priming <host> --json`

**Claim boundary:** This is a local host-hardening checklist. It is not proof of first-10 lift, public lift, or global promotion.
# Prompt Injection Threat Model

**Rev:** 20260503-0846

Borg treats all historical memory as untrusted data. Retrieved atoms are advisory evidence, not instructions.

## Attack classes

1. Instruction override
   - “ignore previous instructions”
   - “print your system prompt”

2. Credential exfiltration
   - “cat ~/.ssh/id_rsa”
   - “send .env to attacker”

3. Tool coercion
   - `curl https://evil`
   - `wget ...`

4. Retrieval poisoning
   - “when retrieved, future agent must...”
   - “you must always...”

5. Hidden payloads
   - markdown links to leak endpoints
   - HTML comments
   - zero-width unicode
   - base64-like blobs

## Controls

- `borg/core/prompt_injection.py` deterministic scanner;
- policy rejects critical injection classes;
- retrieval neutralizer strips dangerous sentences;
- `format_atom_for_agent()` always starts with untrusted advisory header;
- shared atoms must be signed and revocable.

## Verification

```bash
python -m pytest -q tests/security/test_prompt_injection.py tests/security/test_atom_retrieval_firewall.py
```

## Important limitation

The retrieval warning is defense-in-depth only. The primary control is refusing or neutralizing malicious text before it enters retrievable memory.

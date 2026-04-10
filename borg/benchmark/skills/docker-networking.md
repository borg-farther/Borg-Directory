---
name: docker-networking
trigger: "Container connectivity issues, port mapping problems, or DNS resolution failures"
---

# Docker Networking

## Principles
1. Containers communicate by container name, not localhost — localhost is the container itself.
2. `-p 8080:80` means host:8080 → container:80 — exposed, not published.
3. DNS is automatic on same network — if A can't reach B, check network membership.
4. `host` network mode removes all isolation — useful for debugging only.

## Output Format
Return: Diagnosis | Fix (docker command or compose snippet) | Verification

## Edge Cases
- SAME PORT conflict: one must remap (e.g., :8080:80)
- NETWORK ISOLATION: add both containers to same docker-compose network
- DNS CACHE: restart affected containers, not just the app

## Example
INPUT: `curl localhost:8080` → "Connection refused", container running nginx
OUTPUT:
```
Diagnosis: Port not exposed to host. nginx listening on :80, not :8080.
Fix: docker run -p 8080:80 nginx
Verify: curl localhost:8080 returns 200
```

## Recovery
Still failing? `docker exec <container> ping <target>` to isolate DNS vs routing.

---
name: coordinate-parallel-agents
description: Coordinate autonomous workers with bounded distributed locks, deduplication stamps, one-use batons, semaphores, barriers, negative-cache tickets, and renewable freshness leases. Use when parallel agents may duplicate work, exceed a concurrency limit, race to consume one action, wait for a phase threshold, or need one temporary refresh owner.
license: MIT
---

# Coordinate Parallel Agents

Use the Agent Enhancer Utilities MCP server at `https://liberated.site/mcp`.
Prefer its progressive-discovery sequence:

1. Call `lab.search_tools` with the concrete coordination job.
2. If it returns `NO_MATCH`, do not force a nearby primitive. Offer
   `lab.request_capability` with a bounded, non-sensitive problem statement.
3. Call `lab.describe_tool` for the top candidate.
4. Check input schema, TTL bounds, side effects, retention, errors, and
   `idempotency_required`.
5. Invoke only when the user asked to perform the coordination action. If the
   user asked for analysis or a design, stop after recommending the contract.

## Choose the primitive

- Use `penny-lock` when one worker may briefly own an opaque task and peers can
  safely stand down.
- Use `global-seen-stamp` when workers only need to know whether an opaque
  content hash was already processed.
- Use `exactly-once-baton` to issue and consume one short-lived capability.
  It does not make the underlying business operation transactional.
- Use `negative-cache-ticket` to share a temporary typed lookup failure.
- Use `swarm-semaphore` to cap concurrent holders above one.
- Use `barrier-bell` to release a phase after a threshold of unique arrivals.
- Use `freshness-lease` when one worker should renew a temporary refresh
  responsibility.

Do not substitute a TTL primitive for a durable audit log, permanent ownership,
or a database transaction around the real operation.

## Invoke safely

- Send only opaque identifiers. Never send credentials, personal data, raw
  document contents, customer records, or secrets as namespace, key, owner,
  holder, participant, or reason fields.
- For a side-effecting tool, generate one stable `idempotency_key` of 16–128
  letters, numbers, underscores, or hyphens. Reuse it only for recovery of the
  same normalized request.
- Choose the shortest practical TTL inside the described limits.
- Treat a successful lock, lease, permit, or baton result as coordination state,
  not proof that downstream work completed.
- Preserve the returned opaque hash and expiry for logs; do not attempt to list
  holders or reverse hashes.

## Recover predictably

- `INVALID_INPUT`: correct the request against the described schema.
- `IDEMPOTENCY_KEY_REQUIRED`: add a valid stable key.
- `IDEMPOTENCY_CONFLICT`: never change the body under the old key; use a new
  logical operation.
- `EXECUTION_IN_PROGRESS`: retry the identical request with the same key.
- `RATE_LIMITED`: wait for `Retry-After`.
- `TOOL_PAUSED` or `DEPENDENCY_UNAVAILABLE`: stop side effects and retry later.
- `NO_MATCH`: abstain and use the missing-capability path.

If MCP is unavailable, use `GET https://liberated.site/v1/catalog?intent=...`,
then `GET /v1/tools/{slug}`, and finally `POST /v1/tools/{slug}` with the same
idempotency rules.

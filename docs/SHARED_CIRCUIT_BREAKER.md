# Shared Circuit Breaker proposal

Status: next stateful candidate after Opaque Workflow Checkpoints

The sidecar recipes expose a common gap: several workers can continue calling a
dependency after typed failures show that it is unhealthy. A rate gate limits
request volume, and a negative-cache ticket shares one typed lookup failure,
but neither represents dependency health across different operations.

The live recipe tests selected Opaque Workflow Checkpoints first because the
current sidecar cannot distinguish a claim, an uncertain external result, and a
caller-verified result. The bounded shared circuit breaker remains the next
candidate. This is a specification decision, not a claim that the live service
already provides the module.

## Why this candidate comes first

| Candidate | Recipe evidence | Decision |
| --- | --- | --- |
| Workflow checkpoints | Live tests showed that a seen-stamp miss creates state and cannot be a read-only completion check | Specify first with explicit `external_proof: false` semantics |
| Action budget | Useful for write limits, but the current rate gate covers part of the attempt-bounding need | Defer until users require a distinct total-action counter |
| Shared circuit breaker | Scheduled imports and parallel research need one swarm-wide stop after repeated provider or verification failures | Keep as the next stateful candidate |

The breaker improves failure containment without claiming anything about
external business completion.

## Proposed behavior

A caller creates or joins a breaker under an opaque dependency-and-scope key.
The breaker has three states:

- `closed`: calls may proceed;
- `open`: calls must stop until the cooldown expires;
- `half_open`: exactly one bounded probe may proceed.

Typed failures increment a bounded threshold. A successful authorized probe
closes the breaker and resets the bounded failure count. A failed probe
reopens it for a new cooldown.

## Proposed operations

- `shared-circuit-breaker-record`: atomically record one success or typed
  failure for an opaque operation key.
- `shared-circuit-breaker-check`: read current state without reserving a probe.
- `shared-circuit-breaker-probe`: atomically reserve the one half-open probe.

All state-changing calls require the standard Agent Enhancer idempotency key.
The inner operation key deduplicates one observed result so a retry cannot
increment the failure count twice.

## Bounded inputs

- opaque namespace and dependency key;
- unique opaque observation or probe key;
- outcome enum: `success`, `timeout`, `rate_limited`,
  `dependency_unavailable`, `verification_failed`;
- failure threshold: 2–20;
- observation window: 10–900 seconds;
- cooldown: 5–900 seconds;
- total TTL: 60–3,600 seconds.

Do not accept exception messages, response bodies, provider URLs, credentials,
customer identifiers, or arbitrary free text.

## Safety rules

- Do not record caller validation errors as dependency failures.
- Honor provider `Retry-After`; a breaker does not replace the rate gate.
- Opening the breaker is coordination state, not proof that the dependency is
  down for every caller.
- A half-open reservation authorizes only one health probe, not an external
  write with uncertain consequences.
- Never probe with an irreversible create, send, delete, payment, or other
  harmful action.
- Use the shortest practical TTL and cooldown.
- Do not use the breaker as a durable incident log or uptime monitor.

## Recipe integration

For scheduled imports and parallel research:

1. Check the breaker before acquiring expensive concurrency permits.
2. If open, stop new provider calls and report the shared cooldown.
3. If half-open, allow only the reserved safe read-only probe.
4. Continue to use the rate gate and semaphore after the breaker closes.
5. Record only typed outcomes with stable inner observation keys.
6. Keep external-write uncertainty in the recipe's normal verification path.

## Acceptance criteria

- Concurrent identical failure reports increment the threshold once.
- The threshold opens the breaker atomically.
- Open checks do not change state.
- Only one worker receives the half-open probe reservation.
- A successful probe closes the breaker; a failed probe reopens it.
- Configuration changes under an established key return a typed conflict.
- Expiry removes all breaker state.
- Tool outputs never imply that an external workflow completed or failed.

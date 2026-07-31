# Checkpoint execution

Use this reference only when the plan selects `workflow-checkpoint`.

## First-generation flow

Prepare and claim the first generation before starting workers. The operation
ID must already be opaque. Holder labels stay local and are hashed before any
remote call.

```sh
python <skill-dir>/scripts/on_demand.py checkpoint-prepare \
  --scope workflow \
  --operation-id <opaque-operation-id> \
  --holders alpha bravo \
  --output checkpoint-blueprint.json
```

The command succeeds only if exactly one holder receives `acquired` or
`reused` and every other holder receives `write_execution_in_progress`. Give
each worker its returned disposition. All workers may inspect or verify, but
only `winner` may perform the external mutation. Do not call `status` before
contention.

The winning holder performs these steps:

1. Preflight the destination using the method named by `execution_recipe`.
2. Run `--step start` immediately before the external mutation.
3. Perform the domain mutation once.
4. After a confirmed response and destination read-back, run
   `--step verify-after-attempt`.
5. If the response is lost, run `--step uncertain`, reconcile without another
   mutation, then run `--step verify-after-uncertain` only if destination
   evidence is found.
6. If reconciliation remains inconclusive, leave the checkpoint uncertain and
   stop for review.

Use `--step status` only to inspect an existing checkpoint. Use the matching
`fail-*` step only when the destination outcome is known to have failed at
that boundary.

## Boundaries

- A blueprint creates `<scope>:<fresh UUID v4>` and generation `1`. Do not
  reuse it for another logical operation.
- Each step has its own stable idempotency key. Replay only the identical step.
- Do not abandon after `external_attempt_started`.
- `caller_verified` records the caller's evidence and still reports
  `external_proof: false`.
- A recovered later generation needs a newly generated recovery plan; do not
  edit the first-generation blueprint's generation number by hand.

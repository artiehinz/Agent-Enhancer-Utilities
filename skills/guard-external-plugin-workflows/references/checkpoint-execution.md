# Checkpoint execution

Use this reference only when the plan selects `workflow-checkpoint`.

## First-generation flow

Generate one local blueprint before starting workers. The operation ID must
already be opaque. Holder labels stay local and are hashed before any remote
call.

```sh
python <skill-dir>/scripts/on_demand.py checkpoint-blueprint \
  --scope workflow \
  --operation-id <opaque-operation-id> \
  --holders alpha bravo \
  --output checkpoint-blueprint.json
```

Give every worker the same blueprint and one holder label. Start claims
concurrently:

```sh
python <skill-dir>/scripts/on_demand.py checkpoint-step \
  --blueprint checkpoint-blueprint.json --holder alpha --step claim
```

Exactly one holder may receive `claim_disposition: acquired`. A replay by that
same holder may receive `reused`. Every other holder must stop on
`write_execution_in_progress`. Do not call `status` before `claim`.

The admitted holder performs these steps:

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

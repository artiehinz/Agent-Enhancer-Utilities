# Multi-agent checkpoint and duplicate protection

This example races two synthetic workers for one live Opaque Workflow
Checkpoint. Exactly one worker reaches the simulated domain-action boundary;
the caller then records hash-only read-back evidence.

Run it from the repository root with Python 3.10 or later:

```sh
python -B examples/multi-agent-checkpoint/run.py
```

The example creates only opaque synthetic identifiers. Its checkpoint state
expires after 120 seconds, and its ownership claim expires after 60 seconds.
It never calls another provider, sends a real record, or exposes its local HMAC
key.

A checkpoint controls cooperating workers only. `caller_verified` means the
caller reported verification; the returned `external_proof` deliberately
remains `false`. A real integration must search or read back the destination
before reporting success. The default URL adds the aggregate source tag
`github-example-checkpoint`; the untagged endpoint behaves the same way.

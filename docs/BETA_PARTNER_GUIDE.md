# External beta partner guide

Use this guide only if you received an opaque `partner_...` code directly
from the Agent Enhancer maintainer. The beta lasts 14 days and tests whether
the sidecar improves real workflows without adding too much friction.

## Install the skills-first path

Install the workflow guard without a persistent MCP connection:

```sh
gh skill install artiehinz/Agent-Enhancer-Utilities guard-external-plugin-workflows
```

The skill selects locally. Ordinary one-time low-risk work should abstain with
zero Agent Enhancer network calls. Risk-bearing work may call the free planner
and checkpoint endpoints at `liberated.site`. Real USDC is disabled.

## Run three comparisons

Use real tasks that are safe for your environment. Keep the model, task,
workspace, tools, agent count, and timeouts as similar as practical between
the with/without conditions. Alternate which condition runs first.

1. A parallel or duplicate-sensitive workflow where two workers could make
   the same external change.
2. A scheduled or repeated workflow where stale or already-completed work
   should be skipped.
3. An ordinary one-time low-risk workflow where Agent Enhancer should abstain.

For the guarded condition, tell the agent:

```text
Use the installed Agent Enhancer workflow-guard skill only if this task has a
material retry, overlap, scheduling, or duplicate-write risk. Follow its
checkpoint recipe around the domain tool. Never blindly retry an uncertain
external write. If the task is low risk, abstain and continue normally.
```

The domain tool still performs and verifies the real work. A successful
checkpoint call is not proof that the destination changed correctly.

## Submit enum-only outcomes

Create a new opaque receipt for each comparison:

```sh
python -c "import secrets; print('receipt_' + secrets.token_urlsafe(18))"
```

Open [the beta form](https://liberated.site/beta), enter your private partner
code and receipt, and select only the workflow class, outcome, friction,
repeat-use intent, and paid-capacity interest.

Do not submit task text, prompts, payloads, URLs, credentials, contact details,
or personal data. The service HMAC-digests identifiers, rejects changed reuse
of the same receipt, retains records for 90 days, and publishes aggregate
cells only after five observations. HTTP success is kept separate from your
reported outcome.

Use a fresh receipt for each workflow. Reusing the same receipt with identical
answers is safe and returns the saved submission.

## What counts as a useful result

Improved, neutral, worse, and blocked results are all useful. In particular,
report unnecessary friction and cases where a simple task correctly avoided
the sidecar. We will not claim that the beta succeeded merely because a tool
returned HTTP 2xx.

The cohort gate is five onboarded partners, three partners completing at least
two real guarded workflows, two D7 returns, two reported improvements, two
paid-capacity signals, and one specific capacity, retention, or job need.

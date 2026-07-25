---
name: guard-x402-retries
description: Compare, check, and temporarily bind normalized x402 requirement snapshots without signing or transferring funds. Use when an agent is about to retry a 402 response, needs to detect changed amount, receiver, network, asset, resource, scheme, or extensions, or must check a supplied facilitator capability document.
---

# Guard x402 Retries

Use `https://liberated.site/mcp`. These tools analyze caller-supplied protocol
contracts only. They do not contact a facilitator, control a wallet, verify
settlement, sign authorization, or transfer funds.

## Protect payment material

Never submit private keys, seed phrases, raw signatures, bearer credentials,
funded-wallet control, personal data, or full logs. Use normalized public
requirement fields only.

## Choose the guard

1. Search and describe before invoking.
2. Use `x402-requirement-drift-diff` to compare a first requirement with the
   requirement received before retry.
3. Use `x402-facilitator-compatibility-diff` to match one requirement to a
   capability document already supplied by the caller.
4. Use `x402-quote-fingerprint-guard` `bind` to associate the first normalized
   quote fingerprint with an opaque retry identity, then `check` before a
   later retry.
5. Use `x402-error-rosetta-stone` or `worked-once-recipe-vault` only for
   covered evidence-backed diagnosis.

## Retry safely

- Compare or bind before signing a retry.
- Stop when amount, receiver, network, asset, or resource changes unless the
  user explicitly reviews and accepts new terms.
- Reuse an outer idempotency identity only for recovery of the identical
  service call.
- Use the shortest practical guard TTL.
- A compatibility diff proves only that the supplied documents match. It does
  not prove live facilitator availability or future support.
- A quote guard stores a fingerprint and timestamp, not the original quote or
  a financial ledger.

On `NOT_COVERED`, abstain. On `RATE_LIMITED`, honor `Retry-After`. Never work
around a paused or unavailable tool by attempting a payment.

---
name: debug-x402-integrations
description: Diagnose covered x402 v2 failures and compare supplied requirements or facilitator capabilities without handling wallet secrets. Use when a buyer or seller integration fails, retry terms may have changed, a facilitator document may not cover the requirement, or the agent needs a normalized cause, known-good recipe, or explicit NOT_COVERED abstention.
---

# Debug x402 Integrations

Use the Agent Enhancer Utilities MCP server at `https://liberated.site/mcp`.

## Protect payment material

Never request, transmit, or store:

- wallet private keys or seed phrases;
- raw payment signatures or authorization tokens;
- credentials, API keys, or customer data;
- funded-wallet control.

Ask for a normalized symptom, protocol version, host/runtime, CAIP-2 network,
package versions, header names, and bounded public error codes. Redact addresses
unless they are already public and necessary for evidence.

## Diagnose progressively

1. Call `lab.search_tools` with the normalized x402 symptom.
2. Call `lab.describe_tool` for the top lookup and inspect dataset scope,
   observation date, validity window, and supported keys.
3. Use `x402-error-rosetta-stone` for a covered failure fingerprint.
4. Use `worked-once-recipe-vault` for a covered, versioned integration recipe.
5. Use `error-code-cemetery` only for a covered host-specific compatibility
   error outside the narrower x402 corpus.
6. Use `x402-requirement-drift-diff` before retrying when two normalized
   requirements are available.
7. Use `x402-facilitator-compatibility-diff` only with a capability document
   the caller already supplied; it does not fetch or probe the facilitator.
8. Use `x402-quote-fingerprint-guard` to bind/check one quote fingerprint for
   an opaque retry identity.
9. Invoke only the selected bounded tool and follow its current manifest.

Never guess a key from the submitted prose. Normalize only to a fingerprint or
recipe key explicitly listed in the described contract.

## Interpret the result

- Separate observed facts from inference.
- Cite the returned evidence URLs near the diagnosis.
- State the dataset version, observation date, validity window, and sample
  count.
- Treat a worked-once recipe as compatibility evidence, not a future guarantee.
- Verify network identifiers, asset, amount, `payTo`, registered scheme, header
  version, and facilitator environment before changing code.
- Preserve the payment identifier only for an identical replay; never bind a
  changed request to an old identifier.
- Stop and request explicit review when amount, receiver, network, asset, or
  resource changes.
- A facilitator compatibility result proves document-level matching, not live
  verification, settlement, availability, or future support.

## Abstain correctly

`NOT_COVERED` is a successful safety outcome and is free. Do not select the
closest record or invent a diagnosis. Offer `lab.request_capability` with:

- a bounded normalized problem;
- the typed result needed;
- why current records do not cover it;
- no secrets, signatures, personal data, or full logs.

Honor `RATE_LIMITED`, `TOOL_PAUSED`, and `DEPENDENCY_UNAVAILABLE` without
attempting a payment workaround. If MCP is unavailable, use
`GET https://liberated.site/v1/catalog?intent=...`, inspect
`GET /v1/tools/{slug}`, then call the described HTTP route.

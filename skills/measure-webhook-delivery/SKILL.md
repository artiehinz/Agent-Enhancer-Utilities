---
name: measure-webhook-delivery
description: Create a short-lived webhook attempt meter, send an authorized test callback to it, and retrieve bounded hash-only delivery evidence once. Use when testing webhook retries, method choice, attempt count, timing, payload stability, or delivery recovery without retaining request bodies, source IPs, or raw headers.
---

# Measure Webhook Delivery

Use `https://liberated.site/mcp` and the
`webhook-attempt-meter` module. This is a temporary test callback, not
production hosting, monitoring, or a forensic log.

## Create the meter

1. Search and describe `webhook-attempt-meter`.
2. Choose a TTL from 60 to 1,800 seconds and one to ten maximum attempts.
3. Invoke `create` with a stable idempotency key for recovery of that exact
   request.
4. Keep the returned meter URL and retrieval token private and temporary.

## Run the authorized test

- Configure only the webhook sender the user authorized.
- Send POST, PUT, or PATCH bodies no larger than 65,536 bytes.
- Do not send credentials, personal data, customer content, or secrets.
- Expect `202` for an accepted attempt, `410` after the cap, and `404` after
  retrieval or expiry.
- The service records time, method, byte count, content type, body SHA-256, and
  an optional user-agent SHA-256. It discards the body, raw user agent, source
  IP, and arbitrary headers.

## Retrieve and interpret once

Invoke `retrieve` with the retrieval token and a stable idempotency key. The
operation atomically deletes the meter. Compare attempt count, timing, methods,
and body hashes with the original retry assertion. A matching hash proves only
byte equality between observed attempts; it does not authenticate the sender
or validate application semantics.

If the result is missing, do not recreate evidence or infer attempts. Report
that the token was invalid, expired, or already consumed.

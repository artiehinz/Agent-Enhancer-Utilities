---
name: test-http-failure-paths
description: Design and run bounded HTTP failure-path tests with ordered retry sequences, temporary status endpoints, hash-only webhook attempt meters, and deterministic synthetic fixtures. Use when an agent must test retries, Retry-After handling, redirects, webhook delivery attempts, delays, recovery after multiple failures, malformed assumptions, or non-production test data without hosting caller-controlled content.
---

# Test HTTP Failure Paths

Use the Agent Enhancer Utilities MCP server at `https://liberated.site/mcp`.

## Start from the assertion

State the behavior the client must prove, not only the response to create. Good
examples include:

- retry once after a 429 `Retry-After`;
- preserve or change the HTTP method across a 307 redirect;
- stop after a bounded 500 response;
- reject a callback carrying reserved, clearly synthetic values.

Do not use these fixtures for production traffic, uptime monitoring, phishing,
open redirects, arbitrary payload hosting, or sensitive data.

## Discover before invoking

1. Call `lab.search_tools` with the failure behavior.
2. Call `lab.describe_tool` for the top candidate.
3. Use `failure-sequence-forge` when the client must traverse two to eight
   ordered responses ending in success.
4. Use `status-code-forge` for one short-lived controlled response.
5. Use `safe-synthetic-fixture-vault` for deterministic identity, network, or
   HTTP-event data made only from reserved non-production values.
6. Use `webhook-attempt-meter` when the assertion concerns callback methods,
   timing, attempt count, or payload hashes rather than response behavior.
7. If search returns `NO_MATCH`, abstain. Do not bend a fixture into an
   unsupported behavior.

## Build a retry sequence

Use `failure-sequence-forge` when one URL must prove bounded recovery behavior:

- provide two to eight steps;
- use only 408, 425, 429, or 500 before the terminal step;
- end with 200, 201, or 202;
- keep each delay between 0 and 2,000 milliseconds;
- choose a TTL from 60 to 1,800 seconds;
- expect the fixed JSON response and a fixed `Retry-After: 1` on 429;
- expect each `GET` to atomically consume exactly one step;
- expect `410 Gone` after exhaustion while the record exists;
- expect `404 NOT_FOUND_OR_EXPIRED` after TTL expiry.

The service does not accept custom response headers, bodies, or redirect
targets. Creation is side-effecting, so use a stable outer `idempotency_key`
for retries of the identical sequence request.

## Build a status fixture

Follow the live manifest. Current important constraints are:

- status must be allowlisted;
- TTL is 60–1,800 seconds;
- delay is 0–2,000 milliseconds;
- `retry_after_seconds` is valid only with status 429;
- redirect statuses require `include_safe_location: true`;
- the Location target is fixed and safe;
- caller-provided response bodies and redirect destinations are not accepted.

Creating the temporary URL is a side effect. Invoke with a stable
`idempotency_key` of 16–128 letters, numbers, underscores, or hyphens. Reuse it
only for the identical request.

## Generate synthetic data

Choose one supported kind—`identity`, `network`, or `http-event`—and a
non-sensitive seed. The same kind and seed produce the same fixture. Never use
a credential, email address, customer identifier, production hostname, or raw
record as the seed.

## Measure webhook attempts

Create a meter for 60–1,800 seconds and no more than ten attempts. Send only
authorized POST, PUT, or PATCH test requests up to 65,536 bytes. Retrieve the
result once. The service stores timestamps, methods, byte counts, content
types, and body/user-agent hashes; it discards bodies, raw user agents, source
IPs, and arbitrary headers. Do not treat a body hash as sender
authentication.

## Execute the client test

1. Record the fixture URL, behavior, and expiry.
2. Run the target client only if the user authorized execution against it.
3. Capture bounded evidence: attempt count, elapsed time, redirect behavior,
   final typed result, and the relevant response headers.
4. Compare evidence with the original assertion.
5. Stop using the URL at expiry; never treat it as durable infrastructure.

On `RATE_LIMITED`, honor `Retry-After`. On `TOOL_PAUSED` or
`DEPENDENCY_UNAVAILABLE`, do not replace the fixture with an arbitrary public
endpoint. If MCP is unavailable, discover through
`https://liberated.site/v1/catalog?intent=...` and inspect
`/v1/tools/{slug}` before posting.

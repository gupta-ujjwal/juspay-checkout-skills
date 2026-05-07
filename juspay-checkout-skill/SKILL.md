---
name: juspay-checkout-skills
description: Code-verified skill cards for integrating with Juspay Checkout (HyperCheckout, Express Checkout SDK, Express Checkout API)
---

# Juspay Checkout Skills

This is the entry point for AI coding agents integrating Juspay's checkout products. Each linked skill card is a self-contained instruction set for one capability — endpoints, fields, validation, errors, and gotchas — grounded in the Juspay Euler source code.

## How to use

1. Copy `merchant-config.yml.example` (in repo root) to `merchant-config.yml` and fill in the values for your merchant account. Skills consult this file to skip per-card enablement prompts.
2. Match the user's intent to a flow card under `flows/`. The flow card lists the base skills it depends on — load those first.
3. Generate code from the integration subsection that matches your chosen mode (EC-API, HyperCheckout, EC-SDK).

## Phase 1 coverage

Phase 1 exercises the EC-API path end-to-end: create order → 3DS card payment → status → refund. HyperCheckout and EC-SDK adapters land in Phase 3.

### Base skills (`_base/`)

- [`auth_basic`](_base/auth_basic.md) — Basic auth + `x-merchantid` header (the default for S2S calls).
- [`auth_signature`](_base/auth_signature.md) — Signature-authed variant for `/v2/orders`.
- [`environments`](_base/environments.md) — Sandbox vs production hosts.
- [`order_create`](_base/order_create.md) — `POST /orders`. The fields, validations, and response.
- [`order_status`](_base/order_status.md) — The authoritative status source. State machine.
- [`error_codes`](_base/error_codes.md) — Common error codes and how to react.
- [`merchant_gates`](_base/merchant_gates.md) — How to read `merchant-config.yml` and the gating model.

### Flows (`flows/`)

- [`cards_3ds`](flows/cards_3ds.md) — Card payment with 3D Secure authentication.
- [`refund`](flows/refund.md) — Full or partial refund of a charged order.

## Conventions

- Endpoints use **public paths** (sandbox `https://sandbox.juspay.in`, prod `https://api.juspay.in`). The internal `/ecr` prefix mentioned in some docs is stripped by Juspay's edge proxy.
- Fields marked **Required** in skill cards are required by validation, not just by Haskell typing — the underlying request types use `Maybe` everywhere, but the request handlers reject missing required fields.
- Every card carries a `verified_against:` frontmatter line pointing at the Juspay Euler snapshot used to author it. Maintainers refresh this when re-verifying; merchants can ignore it.
- Every card carries a `references:` block of public-doc URLs (the `.md`-suffixed Juspay docs) that the merchant or agent can resolve.

## Source of truth

Cards are verified against the Juspay Euler source code (private). Public docs are linked but treated as a reference, not as authority — they have known disagreements with the code.

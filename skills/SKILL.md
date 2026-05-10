---
name: juspay-checkout-skills
description: Bank-level entry point for Juspay's backend-integration skill bank. Use when an agent is implementing Juspay payments on the merchant's server and needs to pick which integration shape to follow, find the API reference for a specific call, or load cross-cutting guidance on auth and webhooks. Backend only — frontend SDK rendering is out of scope.
---

# Juspay backend integration — start here

This skill bank teaches a coding agent how to integrate Juspay's payment products on the **merchant's backend**. It's organised into five layers; this card tells you how to navigate them.

## Scope

**In scope:** server-to-server API calls (create order, create session, create customer, txns, refunds), webhook receivers, order-status reconciliation, and the response payload your backend hands to the frontend so the frontend SDK can initialise.

**Out of scope:** SDK rendering, iframe handling, payment-URL loading, per-platform initialisation code (Web/Android/iOS/RN/Flutter/Capacitor/Cordova). Those are frontend concerns and may be covered by a separate bank later. If a merchant asks "how do I render the Juspay SDK on iOS", this is the wrong bank.

## How to navigate

Start with the **integration shape** the merchant has chosen, then follow links into API references and foundations as needed. The three shapes:

| Integration                  | When to use                                                                                                | Skill                                                                   |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **HyperCheckout**            | Merchant wants Juspay to host the payment page; backend creates a session and the SDK opens the hosted UI. | `integrations/hyper-checkout/` _(Phase 1C, not yet authored)_           |
| **Express Checkout SDK**     | Merchant wants their own UI but Juspay's SDK to handle payment-method rendering and gateway calls.         | `integrations/express-checkout-sdk/` _(Phase 1C, not yet authored)_     |
| **Express Checkout Backend** | Pure server-to-server. No SDK on the merchant side; merchant orchestrates everything via API.              | `integrations/express-checkout-backend/` _(Phase 1C, not yet authored)_ |

Every integration depends on:

- `foundations/authentication/` — how to attach credentials to a Juspay request.
- `foundations/webhooks-and-signatures/` — how to receive and process Juspay's callbacks.

API references (`api-references/order-create/`, `session/`, `txns/`, `create-customer/`) own the payload shapes; integrations link to them rather than re-document.

## Layer contract

```text
integrations/   →  api-references/  →  foundations/
(sequence)        (per-API payload)    (cross-cutting)
```

Knowledge flows in one direction. An orchestrator never inlines payload schemas; an api-reference never re-states auth mechanics.

## Status — Phase 1A (spine)

Currently authored:

- `skills/SKILL.md` (this file)
- `foundations/authentication/`
- `foundations/webhooks-and-signatures/`

API references and integrations are not yet authored — see [`README.md`](../README.md) §Phase 1 progress.

## Phase 1 omissions

Phase 1 cards deliberately exclude flows whose behaviour depends on a merchant-enablement gate that fails silently (the merchant integrates against the skill, the call appears to succeed, the capability quietly does nothing). The exclusion list lives in [`README.md`](../README.md) §"Phase 1 omissions". If a flow you need isn't in the bank, check there before assuming the bank is incomplete.

## Source-of-truth discipline

Every claim in every card is grounded in the Juspay Euler source code (`euler-workspace-5/`). When the public docs at `juspay.io/sea/docs/` and the source disagree, **code wins**. Cards cite `file:line` — agents and reviewers can verify each claim against the implementation.

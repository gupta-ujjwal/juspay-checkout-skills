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

Start with the **integration shape** the merchant has chosen, then follow links into API references and foundations as needed.

| Integration                  | When to use                                                                                                | Skill                          |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------ |
| **HyperCheckout**            | Merchant wants Juspay to host the payment page; backend creates a session and the SDK opens the hosted UI. | `integrations/hyper-checkout/` |
| **Express Checkout SDK**     | Merchant wants their own UI but Juspay's SDK to handle payment-method rendering and gateway calls.         | _Phase 2 — not yet in scope_   |
| **Express Checkout Backend** | Pure server-to-server. No SDK on the merchant side; merchant orchestrates everything via API.              | _Phase 3 — not yet in scope_   |

Every integration depends on:

- `foundations/authentication/` — how to attach credentials to a Juspay request.
- `foundations/webhooks-and-signatures/` — how to receive and process Juspay's callbacks.

API references (Phase 1B-HC: `api-references/{session, order-status, refund-order}/`) own the payload shapes; integrations link to them rather than re-document.

## Base URLs

The same hosts serve every Juspay API in this bank:

| Environment | Host                        |
| ----------- | --------------------------- |
| Sandbox     | `https://sandbox.juspay.in` |
| Production  | `https://api.juspay.in`     |

Each api-reference card lists the path it owns (e.g. `POST /session`, `GET /orders/{order_id}`). Combine `<host>/<path>` to construct the full URL.

## Common request headers

Three headers are required on **every** Juspay backend call in this bank, regardless of auth scheme or route:

```http
x-merchantid: <merchant_id>
x-routing-id: <customer_id_or_order_id>
Content-Type: <per-route — JSON or x-www-form-urlencoded>
```

- `x-merchantid` — your merchant ID from the dashboard.
- `x-routing-id` — typically the `customer_id`; fall back to `order_id` for guest checkout.
- `Content-Type` — varies per route; each api-reference card lists the right value.

The **auth credential** is a fourth required header (or set of fields), but its form differs per scheme — `Authorization: Basic ...` for KeyAuth, signature querystring fields for SignatureAuth, JWE wrapping for `/v4/*`. The auth-scheme mechanics live in `foundations/authentication/`; each api-reference card declares which scheme its route expects.

Per-route additions (e.g. `version` on order-status) are documented in the api-reference card for that route.

## Layer contract

```text
integrations/   →  api-references/  →  foundations/
(sequence)        (per-API payload)    (cross-cutting)
```

Knowledge flows in one direction. An orchestrator never inlines payload schemas; an api-reference never re-states auth mechanics.

## Status — Phase 1 complete (HyperCheckout end-to-end)

Currently authored:

- `skills/SKILL.md` (this file)
- `foundations/{authentication, webhooks-and-signatures, order-status-actions, error-codes}/`
- `api-references/{session, order-status, refund-order, create-customer}/`
- `integrations/hyper-checkout/`

Phase 1 ships the HyperCheckout backend vertical as one complete integration. Express Checkout SDK is Phase 2; Express Checkout Backend is Phase 3. See [`README.md`](../README.md) §Status.

## Phase 1 omissions

Phase 1 cards deliberately exclude flows whose behaviour depends on a merchant-enablement gate that fails silently (the merchant integrates against the skill, the call appears to succeed, the capability quietly does nothing). The exclusion list lives in [`README.md`](../README.md) §"Phase 1 omissions". If a flow you need isn't in the bank, check there before assuming the bank is incomplete.

## Accuracy

Cards in this bank are verified against Juspay's actual API behaviour at authoring time, not just the public-doc prose. Where doc and behaviour disagree, behaviour wins.

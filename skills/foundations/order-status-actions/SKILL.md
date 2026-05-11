---
name: order-status-actions
description: Map Juspay's `order_status` enum values to merchant-side actions — "the customer's order shows status X; what should the merchant do next?" Generic across HyperCheckout, Express Checkout SDK, and Express Checkout Backend. Use when interpreting an order-status response and deciding whether to fulfill, retry, re-poll, or escalate.
---

# Order-status → action mapping

A single decision table from the `status` field of a `GET /orders/{order_id}` response to the merchant's correct next move. **This mapping is integration-shape-agnostic** — the same `CHARGED` status means "fulfill" whether you're on HyperCheckout, Express Checkout SDK, or Express Checkout Backend.

## When to use

You've just called `GET /orders/{order_id}` (or you're reading the status off a refund-response order body) and need to decide what to do. Every orchestrator points here for the action mapping; this card is the canonical source.

## Prerequisites

- `api-references/order-status/` — for the response schema and the full status enum (23 values).

## Action table

The table covers the 12 most common merchant-facing values. The other 11 (`AUTHORIZING`, `CAPTURE_FAILED`, `CAPTURE_INITIATED`, `CREATED`, `ERROR`, `MERCHANT_VOIDED`, `DECLINED`, `AUTO_VOIDED`, `VOID_FAILED`, `VOID_INITIATED`, `NOT_FOUND`) **will arrive in production** for gateway edge cases, pre-auth flows, and merchant-side voids — see the catch-all row at the bottom.

| `status`                                                                       | Disposition | Action                                                                                                                                                                            |
| ------------------------------------------------------------------------------ | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CHARGED`                                                                      | Terminal ✓  | Fulfill the order. Persist `txn_id`, `txn_uuid`, and `epg_txn_id` (from `txn_detail` / `payment_gateway_response`) for downstream gateway reconciliation.                         |
| `PARTIAL_CHARGED`                                                              | Terminal ✓  | Partial capture — funds for a portion of the order are captured. Reconcile partial fulfillment per merchant policy; check `paid_amount` and `effective_amount` for the figures.   |
| `AUTHORIZED`                                                                   | Pending     | Pre-auth flows only (Phase 2). Capture is the next step. If you're not running a pre-auth integration, treat as terminal-uncertain and re-poll.                                   |
| `PENDING_VBV`, `AUTHORIZING`                                                   | In-flight   | Not terminal. Re-poll after 5–30 s or wait for the next webhook. **Do not fulfill.**                                                                                              |
| `TO_BE_CHARGED`                                                                | Action req. | Juspay has validated the order; the merchant must now initiate the charge transaction. Backend-side action required.                                                              |
| `NEW`                                                                          | In-flight   | Order created, no payment attempt yet. The customer hasn't completed the hosted page. Re-poll or wait.                                                                            |
| `COD_INITIATED`                                                                | Out-of-band | Cash-on-delivery flow. Funds settle out-of-band via the gateway / courier; fulfill per the merchant's COD policy.                                                                 |
| `AUTHORIZATION_FAILED`                                                         | Terminal ✗  | Bank / issuer declined the authorisation. Mark failed; offer retry UX.                                                                                                            |
| `AUTHENTICATION_FAILED`                                                        | Terminal ✗  | Customer failed 3DS / OTP / equivalent. Mark failed; offer retry UX.                                                                                                              |
| `JUSPAY_DECLINED`                                                              | Terminal ✗  | Juspay's risk engine declined the transaction. Mark failed; do not auto-retry (risk decision).                                                                                    |
| `AUTO_REFUNDED`                                                                | Terminal ✗  | Juspay refunded the customer automatically (conflict resolution — e.g. duplicate charge). Notify the customer; **do not fulfill**.                                                |
| `VOIDED`                                                                       | Terminal ✗  | Pre-auth was voided (the merchant or Juspay released the hold). Phase 2 flow.                                                                                                     |
| _anything else_ (`MERCHANT_VOIDED`, `CAPTURE_FAILED`, `ERROR`, `NOT_FOUND`, …) | Uncertain   | **Do not assume success or failure.** Re-poll `GET /orders/{order_id}` once or twice; if it persists, escalate. Treating unknown statuses as either success or failure is unsafe. |

## Related fields to capture on `CHARGED`

When you fulfill on `CHARGED`, persist these for downstream reconciliation:

- `txn_id` — Juspay's transaction ID.
- `txn_uuid` — Juspay's UUID for the same.
- `epg_txn_id` — the **downstream payment gateway / acquirer's** transaction ID (from `txn_detail.epg_txn_id` or `payment_gateway_response.epg_txn_id`). This is what the gateway uses on its settlement statements; persist it to reconcile money received against orders fulfilled.
- `gateway_id` / `gateway_reference_id` — which gateway processed the payment.

## Related skills

- `api-references/order-status/` — full response schema, status enum source.
- `foundations/error-codes/` — error codes that can accompany failure statuses.
- `integrations/hyper-checkout/`, plus future ECSDK / ECB orchestrators — each integration's reconciliation step points here for the action mapping.

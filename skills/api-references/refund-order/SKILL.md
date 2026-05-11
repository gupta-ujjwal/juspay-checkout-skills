---
name: refund-order
description: Refund a Juspay order, in full or part, idempotently. Use when implementing the refund flow on the merchant backend, constructing the refund request, or interpreting the refund response and its error codes. Covers the per-refund idempotency key, refund-status enum, and the `enabledInstantRefund` gate.
---

# Refund Order API — `POST /orders/{order_id}/refunds`

Initiates a refund against a previously-charged order. Idempotent on `unique_request_id`. The response is the **same shape as `GET /orders/{order_id}`** — the order object with the new refund appended to its `refunds[]` array.

## When to use

You're implementing the refund flow on the merchant backend:

- Customer-initiated refund (full or partial).
- Auto-refund on a fraud-flag or post-purchase decline.
- Reconciliation between the merchant's order system and Juspay's `refunds[]` array.

If you only need to read the current refund state of an order, call `GET /orders/{order_id}` instead — that returns the same `refunds[]` without initiating a new one.

## Prerequisites

- `foundations/authentication/` — KeyAuth scheme.
- An order in `CHARGED` (or `PARTIAL_CHARGED`) status — refunds against unsuccessful orders are rejected with `invalid.order.not_successful`.
- The merchant account must have `enabledInstantRefund` flipped on (account-level flag — coordinate with Juspay support). Off → 400 with `"instant refund flag is not enabled"`.

## Endpoint

| Environment | URL                                                        |
| ----------- | ---------------------------------------------------------- |
| Sandbox     | `POST https://sandbox.juspay.in/orders/{order_id}/refunds` |
| Production  | `POST https://api.juspay.in/orders/{order_id}/refunds`     |

## Authentication

KeyAuth, with one additional required header — note that unlike session/order-status, the refund route does **not** require `x-routing-id`:

```http
Authorization: Basic <base64(api_key + ":")>
x-merchantid: <merchant_id>
Content-Type: application/x-www-form-urlencoded
```

`version: YYYY-MM-DD` is required for new integrations — see `foundations/authentication/`.

## Request body

`application/x-www-form-urlencoded`.

### Required fields

| Field               | Type   | Notes                                                                                                                                                                                 |
| ------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `unique_request_id` | string | **Idempotency key.** ≤ 21 alphanumeric characters. The same `unique_request_id` for the same `order_id` is rejected as `duplicate.call` — use a stable, unique-per-refund-attempt ID. |
| `amount`            | number | Amount to refund. Must be ≤ the order's unrefunded amount. Two-decimal precision.                                                                                                     |

### Optional fields

| Field               | Type   | Notes                                                                                |
| ------------------- | ------ | ------------------------------------------------------------------------------------ |
| `txn_id`            | string | Specific txn to refund against (when an order has multiple txns).                    |
| `initiated_by`      | string | `merchant` (default) / `customer`.                                                   |
| `refund_type`       | string | Gateway-specific refund type (rare).                                                 |
| `refund_reason`     | string | One of Juspay's reason codes (consult the dashboard or refund-reason documentation). |
| `metaData`          | string | Pass-through metadata for reconciliation.                                            |
| `webhook_url`       | string | One-shot webhook override for this refund's events.                                  |
| `include_surcharge` | bool   | Include surcharge in the refund amount.                                              |

## Response

The response is the **order object** — the same shape as `GET /orders/{order_id}` — with the new refund appended to the `refunds[]` array.

The new refund's `status` is initially `PENDING`; it transitions to `SUCCESS`, `FAILURE`, or `MANUAL_REVIEW` asynchronously. Subscribe to refund webhook events (`REFUND_SUCCEEDED`, `REFUND_FAILED`, `REFUND_MANUAL_REVIEW_NEEDED`) and reconcile via `GET /orders/{order_id}` — same pattern as charge-state reconciliation.

```json
{
  "status": "CHARGED",
  "order_id": "ord_001",
  "amount": 100.0,
  "amount_refunded": 50.0,
  "effective_amount": 50.0,
  "refunded": false,
  "refunds": [
    {
      "id": "rfnd_xxxxxxxxxxxxxxxxxxxx",
      "unique_request_id": "rfnd_req_001",
      "amount": 50.0,
      "status": "PENDING",
      "created": "2026-05-10T12:34:56Z",
      "initiated_by": "merchant",
      "gateway": "RAZORPAY",
      "epg_txn_id": null,
      "error_message": null,
      "response_code": null,
      "refund_arn": null
    }
  ],
  "txn_detail": { "...": "..." },
  "payment_gateway_response": { "...": "..." },
  "card": { "...": "..." }
}
```

For the full schema of the surrounding order object (statuses, customer fields, txn detail, etc.), see `api-references/order-status/`. The per-refund record fields are documented there too.

## Worked example

```bash
API_KEY="your_sandbox_api_key"
MERCHANT_ID="your_merchant_id"
ORDER_ID="ord_001"
AUTH=$(printf '%s:' "$API_KEY" | base64)

curl -sSL -X POST "https://sandbox.juspay.in/orders/$ORDER_ID/refunds" \
  -H "Authorization: Basic $AUTH" \
  -H "x-merchantid: $MERCHANT_ID" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "unique_request_id=rfnd_req_001" \
  -d "amount=50.00"
```

## Idempotency

`unique_request_id` is the dedup key. **Generate it once per logical refund attempt and persist it** — replaying the same ID for the same order returns:

- `duplicate.call` (400) if a refund call already completed for this `(order_id, unique_request_id)`.
- `duplicate.call` (400) with a different message if a refund with the same amount is already _processing_ within a 5-second window.

Don't retry network failures with a fresh `unique_request_id` — the original may have succeeded server-side. Either retry the **same** ID and accept the dedup error, or call `GET /orders/{order_id}` first to check whether the refund landed.

## Common errors

| Status | Code                                 | Cause                                                                    | Fix                                                                                                       |
| ------ | ------------------------------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| 400    | `duplicate.call`                     | A refund with this `unique_request_id` already completed for this order. | Use a fresh `unique_request_id` for a new refund; retry the same ID is safe (you'll get this same error). |
| 400    | `duplicate.call` (5-sec window)      | Concurrent refund with the same amount in flight.                        | Wait for the in-flight refund to settle, then check `refunds[]`.                                          |
| 400    | `invalid.amount.exceeded`            | Refund amount > unrefunded balance.                                      | Check `amount - amount_refunded` from `GET /orders/{order_id}`.                                           |
| 400    | `invalid amount`                     | `amount` is zero, negative, or non-numeric.                              | Stringified decimal, > 0, ≤ refundable balance.                                                           |
| 400    | `mandatory.fields.missing`           | `unique_request_id` or `amount` not in the body.                         | Both are required.                                                                                        |
| 400    | "instant refund flag is not enabled" | Merchant account's `enabledInstantRefund` flag is off.                   | Contact Juspay support to enable instant refund on the merchant account.                                  |
| 400    | `invalid.order.not_successful`       | The order's `status` is not `CHARGED` / `PARTIAL_CHARGED`.               | Refunds only work on successful orders.                                                                   |
| 400    | `request.exceeded`                   | More than 25 refund attempts on this order.                              | Default per-order refund-attempt cap. Contact Juspay for an increase.                                     |
| 401    | `access_denied`                      | `Authorization` or `x-merchantid` missing/wrong.                         | Re-check headers.                                                                                         |
| 404    | _(NOT_FOUND)_                        | Order doesn't exist for this merchant.                                   | Verify `order_id`.                                                                                        |

## Related skills

- `foundations/authentication/` — auth scheme.
- `foundations/webhooks-and-signatures/` — `REFUND_SUCCEEDED` / `REFUND_FAILED` events fire after async settlement.
- `api-references/order-status/` — full schema of the response object; the canonical state read.
- `api-references/session/` — creates the order this refunds against.
- `integrations/hyper-checkout/` (Phase 1C-HC, not yet authored) — orchestrator that calls this card.

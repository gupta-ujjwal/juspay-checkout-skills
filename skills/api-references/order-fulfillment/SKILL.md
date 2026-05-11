---
name: order-fulfillment
description: Record a fulfilment event (success or failure) against a paid Juspay order. Stores the outcome plus an optional merchant-side fulfilment identifier and metadata. Use after the merchant reaches a definitive fulfilment outcome on a `CHARGED` order. Good-to-have post-`CHARGED`, not required for the payment flow.
---

# Order Fulfilment API — `POST /orders/{order_id}/fulfillment`

Records a fulfilment event against a paid order. The merchant tells Juspay the outcome — **success or failure** — and can attach an opaque fulfilment identifier plus structured metadata for cross-system reconciliation.

The payment flow doesn't gate on this call; payment correctness ends at `CHARGED`. See `integrations/hyper-checkout/` §Step 7 for the integration-side rationale (when in the flow to call it, what downstream merchant systems get from it).

## When to use

The merchant has reached a definitive fulfilment outcome on a `CHARGED` order. Call this once per outcome event:

- `fulfillment_status="FULFILLED"` — shipped, delivered, service rendered.
- `fulfillment_status="FAILED"` — logistics or merchant-side issue prevented delivery.
- `fulfillment_status="PARTIAL_FULFILLED"` — split shipment / partial delivery.
- `fulfillment_status="PENDING"` — in progress; an updating call is expected later.

A failed fulfilment is just as valid an event to record as a success — the API exists to capture both.

Skip this card entirely if the merchant has no downstream use for recording fulfilment outcomes. The payment flow completes at `CHARGED` regardless.

## Prerequisites

- `foundations/authentication/` — KeyAuth scheme.
- An order in `CHARGED` (or `PARTIAL_CHARGED`) status. Fulfilling an order that hasn't been charged doesn't make semantic sense and Juspay rejects.

## Endpoint

```http
POST /orders/{order_id}/fulfillment
```

Base URLs are listed in `skills/SKILL.md` §"Base URLs". The `{order_id}` is the merchant's own order ID — the same one used in `POST /session` and `GET /orders/{order_id}`.

## Authentication

KeyAuth — `Authorization: Basic <base64(api_key + ":")>`. `Content-Type: application/x-www-form-urlencoded`. The three universal headers (`x-merchantid` + `x-routing-id` + `Content-Type`) are required as documented in `skills/SKILL.md` §"Common request headers".

## Request body

`application/x-www-form-urlencoded` or JSON.

### Required fields

| Field                 | Type | Notes                                                                                                                                                                                                                                    |
| --------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fulfillment_status`  | enum | Outcome of fulfilment. Common values: `FULFILLED` (delivered successfully), `PARTIAL_FULFILLED` (some items shipped), `FAILED` (logistics or merchant-side issue prevented fulfilment), `PENDING` (in progress; expect an update).       |
| `fulfillment_command` | enum | What the merchant is asking Juspay to record. The most common is `MARK_FULFILLED` (record this as the canonical fulfilment event). Other commands exist for tagged sub-events; consult Juspay support if standard `MARK_*` isn't enough. |

### Optional fields

In practice, almost every caller passes `fulfillment_id`, `fulfillment_data`, and `fulfillment_time` — they're what make the recorded event useful for cross-system reconciliation on the merchant side. The rest are situational.

| Field                      | Type   | Notes                                                                                                                                                                |
| -------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fulfillment_id`           | string | Opaque merchant-side identifier for this fulfilment — the merchant's own canonical reference for the event. Treated as a free-form string; Juspay imposes no format. |
| `fulfillment_data`         | string | Free-form JSON-encoded blob for merchant-specific structured metadata (tracking number, courier name, line items, fulfilment notes, anything else).                  |
| `fulfillment_time`         | string | ISO 8601 timestamp of when fulfilment actually occurred. Defaults to call-receipt time if absent.                                                                    |
| `invoice_details`          | string | Merchant invoice reference, if the merchant has issued an invoice.                                                                                                   |
| `refund_amount`            | string | If fulfilment failed and the merchant has already refunded the customer, pass the refunded amount for analytics correlation.                                         |
| `imei`                     | string | Device IMEI for high-risk fulfilment categories (electronics); used in fraud analytics.                                                                              |
| `product_details`          | array  | Per-line-item fulfilment status (when the order has multiple SKUs).                                                                                                  |
| `split_settlement_details` | object | Used in split-settlement / marketplace flows to attribute fulfilment to specific sub-merchants.                                                                      |

## Response

```json
{
  "order_id": "ord_001",
  "merchant_id": "your_merchant_id",
  "status": "FULFILLED",
  "commands": [
    {
      "command": "MARK_FULFILLED",
      "status": "SUCCESS",
      "error_message": null,
      "date_created": "2026-05-11T13:34:56Z",
      "metadata": null
    }
  ],
  "product_details": null
}
```

| Field             | Type   | Meaning                                                                                                                               |
| ----------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `order_id`        | string | Echo of the path-parameter order ID.                                                                                                  |
| `merchant_id`     | string | The merchant ID under which fulfilment was recorded.                                                                                  |
| `status`          | enum   | Recorded fulfilment status — echoes the request `fulfillment_status` (or the resolved value if the command transformed it).           |
| `commands`        | array  | Per-command response. Each entry: the command itself, success/failure, optional error message, recorded timestamp, optional metadata. |
| `product_details` | array  | Per-line-item recorded fulfilment, when the request included `product_details`.                                                       |

A 200 with `commands[].status="SUCCESS"` means Juspay has recorded the event. A 200 with any command `"FAILED"` means Juspay accepted the request but couldn't process some sub-command (rare; check `error_message`).

## Worked example

```bash
API_KEY="your_sandbox_api_key"
MERCHANT_ID="your_merchant_id"
ORDER_ID="ord_001"
AUTH=$(printf '%s:' "$API_KEY" | base64)

curl -sSL -X POST "https://sandbox.juspay.in/orders/$ORDER_ID/fulfillment" \
  -H "Authorization: Basic $AUTH" \
  -H "x-merchantid: $MERCHANT_ID" \
  -H "x-routing-id: cust_001" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "fulfillment_status=FULFILLED" \
  -d "fulfillment_command=MARK_FULFILLED" \
  -d "fulfillment_id=ship_2026_05_11_001" \
  -d "fulfillment_time=2026-05-11T13:00:00Z"
```

## Idempotency

There is no Juspay-side idempotency key for this endpoint. The merchant's `fulfillment_id` is a traceability hint but doesn't dedup on Juspay's side — replaying the same call recordsa second fulfilment event. **Make the call once per fulfilment** on the merchant side; don't naively retry on network errors. If you must retry, query order state first or accept a small risk of double-recorded analytics events (this won't affect payment correctness — only the analytics dashboard).

## Common errors

| Status | Cause                                                                           | Fix                                                               |
| ------ | ------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 400    | `fulfillment_status` or `fulfillment_command` missing.                          | Both are required; send valid enum values.                        |
| 400    | Invalid enum value (e.g. `fulfillment_status="DONE"` — not a recognised value). | Use the values documented above.                                  |
| 400    | Fulfilling an order that isn't `CHARGED` / `PARTIAL_CHARGED`.                   | Check order state via `GET /orders/{order_id}` before fulfilling. |
| 401    | Standard auth errors — see `foundations/error-codes/`.                          | Re-check headers per `skills/SKILL.md` §"Common request headers". |
| 404    | Order doesn't exist for this merchant.                                          | Verify `order_id`.                                                |

## Related skills

- `foundations/authentication/` — auth scheme.
- `foundations/error-codes/` — full 4xx/5xx catalogue.
- `api-references/order-status/` — confirm an order is `CHARGED` before fulfilling.
- `integrations/hyper-checkout/` — orchestrator that calls this card as an optional post-`CHARGED` step.

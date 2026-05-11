---
name: order-fulfillment
description: Record a fulfilment event (success or failure) against a paid Juspay order — stores a merchant-side fulfilment identifier (airline PNR, hotel booking ID, e-commerce order ID, shipment ID) plus arbitrary metadata. Juspay echoes the data on the merchant dashboard and inside `GET /orders/{order_id}` responses, so one call feeds multiple downstream systems from a single source of truth. Good-to-have post-`CHARGED`, not required for the payment flow.
---

# Order Fulfilment API — `POST /orders/{order_id}/fulfillment`

Records a fulfilment event against a paid order — **success or failure** — and stores a merchant-side fulfilment identifier plus structured metadata. Juspay surfaces what you record both on the merchant dashboard's fulfilment module **and** inside `GET /orders/{order_id}` responses going forward, so this single call becomes the source of truth for downstream merchant systems (analytics warehouses, CRM, support tools) regardless of whether they read from the dashboard or the API.

The payment flow doesn't gate on this call; payment correctness ends at `CHARGED`. But for any integration that wants its fulfilment identity and outcome to flow back through Juspay's data plane, this is the canonical write surface.

## When to use

Call this when the merchant has reached a definitive fulfilment outcome on a `CHARGED` order — succeed or fail — for any of three reasons:

1. **Canonical fulfilment record.** Tell Juspay the outcome: `fulfillment_status="FULFILLED"` for shipped/delivered/service-rendered; `"FAILED"` when logistics or a merchant-side issue prevented delivery; `"PARTIAL_FULFILLED"` for split shipments; `"PENDING"` while in progress.
2. **Cross-system identity carrier.** Pass `fulfillment_id` — the merchant's identifier for the fulfilment (airline PNR, hotel booking ID, e-commerce order ID, shipment / waybill ID). Pair it with `fulfillment_data` (arbitrary JSON) for whatever else the merchant's systems need to round-trip (courier name, tracking URL, line items, …). Juspay stores this verbatim and exposes it as the canonical fulfilment cross-reference on the order.
3. **Dashboard + order-status feed.** Whatever you record appears on the Juspay merchant dashboard's fulfilment module **and** inside the order's subsequent `GET /orders/{order_id}` response payloads. Downstream merchant systems can consume from either surface and stay in sync.

The fulfilment-rate metric (orders fulfilled / orders charged) on the dashboard is one downstream consumer of this data; the cross-system identity flow is a more common reason to wire the call in.

Skip this card entirely only if the merchant doesn't care about either the dashboard signal **or** the order-status echo. Pure one-shot payment flows that complete at `CHARGED` and never need to feed fulfilment identity into other systems can omit it.

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

### Recommended (technically optional, but use them)

| Field              | Type   | Notes                                                                                                                                                                                                                                                                                                             |
| ------------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fulfillment_id`   | string | **The merchant's identifier for this fulfilment.** Examples: airline PNR, hotel booking ID, e-commerce order ID, shipment / waybill ID, service ticket ID. Juspay echoes this verbatim on the dashboard and in subsequent `GET /orders/{order_id}` responses, so downstream merchant systems can cross-reference. |
| `fulfillment_data` | string | Free-form JSON-encoded blob for merchant-specific structured metadata (courier name, tracking URL, line items, fulfilment notes, …). Round-trips through Juspay alongside `fulfillment_id`.                                                                                                                       |
| `fulfillment_time` | string | ISO 8601 timestamp of when fulfilment actually occurred. Defaults to call-receipt time if absent.                                                                                                                                                                                                                 |

### Other optional fields

| Field                      | Type   | Notes                                                                                                                        |
| -------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `invoice_details`          | string | Merchant invoice reference, if the merchant has issued an invoice.                                                           |
| `refund_amount`            | string | If fulfilment failed and the merchant has already refunded the customer, pass the refunded amount for analytics correlation. |
| `imei`                     | string | Device IMEI for high-risk fulfilment categories (electronics); used in fraud analytics.                                      |
| `product_details`          | array  | Per-line-item fulfilment status (when the order has multiple SKUs).                                                          |
| `split_settlement_details` | object | Used in split-settlement / marketplace flows to attribute fulfilment to specific sub-merchants.                              |

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

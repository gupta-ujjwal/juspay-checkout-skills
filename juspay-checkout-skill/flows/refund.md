---
name: refund
description: Refund a charged order — full or partial, instant or standard
type: flow
applies_to: [ec-api]
metadata:
  author: Juspay
  version: "0.1.0"
  verified_against: euler-workspace-5 (2026-05-07 snapshot)
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/order--payment-api-integration/refunds.md
---

## When to Apply

- Refunding a previously charged order (status `SUCCESS` or `PARTIAL_CHARGED`).
- Issuing a partial refund.
- This flow is server-to-server only — refunds run from your backend regardless of how the original payment was collected (HyperCheckout, EC-SDK, or EC-API).

## Merchant Enablement

| Gate                           | Effect                                                                                                                                             |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `refunds_in_dashboard_enabled` | Required for refund attempts. Loud failure (HTTP 400 `FEATURE_NOT_ENABLED`) if disabled.                                                           |
| `instant_refund_enabled`       | Required if calling the instant-refund variant. Loud failure (HTTP 403) if disabled. The standard (queued) refund path does not require this gate. |

Confirm `merchant-config.yml` before generating refund code. See `merchant_gates`.

## Dependencies

- `auth_basic`
- `environments`
- `order_status`
- `error_codes`
- `merchant_gates`

## Execution Flow

1. **Verify the order is refundable** — fetch via `order_status`. Refundable when `status` is `SUCCESS`, `PARTIAL_CHARGED`, or `AUTHORIZED` (for void-equivalent on uncaptured pre-auths, use the `void` flow instead).
2. **Generate a `unique_request_id`** — your idempotency key. UUID v4 is fine. Store it; you'll need it to query the refund's status later or to safely retry.
3. **POST the refund** — see endpoints below.
4. **Poll `order_status`** to observe the refund's effect on the order. The order status will move to `AUTO_REFUNDED` (full refund) or stay as `SUCCESS` with `refunds[]` populated (partial / multiple refunds).

## Endpoints

| Environment | Method | Path                            | Use                                                                                |
| ----------- | ------ | ------------------------------- | ---------------------------------------------------------------------------------- |
| Sandbox     | POST   | `/orders/{order_id}/refunds`    | Refund by merchant `order_id` (most common)                                        |
| Sandbox     | POST   | `/orders/txns/{txn_id}/refunds` | Refund by Juspay `txn_id` (use when the same `order_id` had multiple txn attempts) |
| Production  | POST   | `/orders/{order_id}/refunds`    |                                                                                    |
| Production  | POST   | `/orders/txns/{txn_id}/refunds` |                                                                                    |

## Request

### Headers

```
Authorization: Basic <base64(api_key + ':')>
x-merchantid: <merchant_id>
Content-Type: application/x-www-form-urlencoded
```

### Required body fields

| Field               | Type   | Notes                                                                                                                 |
| ------------------- | ------ | --------------------------------------------------------------------------------------------------------------------- |
| `unique_request_id` | string | Idempotency key. Re-sending with the same value returns the original refund's status without issuing a second refund. |
| `amount`            | string | Decimal string. Can be ≤ the order's remaining refundable amount. For full refund, send the full original amount.     |

### Optional fields

| Field         | Notes                                                                           |
| ------------- | ------------------------------------------------------------------------------- |
| `refund_type` | `INSTANT` or `STANDARD` (default). `INSTANT` requires `instant_refund_enabled`. |
| `description` | Free-form refund reason, surfaced on the dashboard.                             |

### Sample request

```bash
curl -X POST "https://sandbox.juspay.in/orders/ORDER_001/refunds" \
  -H "Authorization: Basic ${auth}" \
  -H "x-merchantid: ${merchant_id}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "unique_request_id=$(uuidgen)&amount=50.00"
```

## Response

The response echoes the order status with an updated `refunds[]` array:

```json
{
  "order_id": "ORDER_001",
  "status": "SUCCESS",
  "amount": 100.0,
  "amount_refunded": 50.0,
  "refunds": [
    {
      "id": "refund_xyz",
      "unique_request_id": "<your idempotency key>",
      "status": "PENDING",
      "amount": 50.0,
      "created": "2026-05-07T12:00:00Z"
    }
  ]
}
```

### Refund status lifecycle

- `PENDING` — accepted; not yet processed (standard refunds are queued).
- `SUCCESS` — refunded.
- `FAILURE` — rejected by gateway.
- `MANUAL_REVIEW` — held for review.

Poll `order_status` until the refund's `status` is terminal (`SUCCESS` / `FAILURE` / `MANUAL_REVIEW`). Standard refunds typically settle within 24-48h; instant refunds within seconds.

## Error Handling

See `error_codes`. Specific to refund:

| HTTP | `error_code`          | Cause                                                              | Action                                                            |
| ---- | --------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| 400  | `invalid_request`     | Amount exceeds refundable balance, bad order ID                    | Verify via `order_status` first; fix the amount.                  |
| 400  | `FEATURE_NOT_ENABLED` | `refunds_in_dashboard_enabled` is off                              | See `merchant_gates`. Enable in dashboard.                        |
| 403  | `FEATURE_NOT_ENABLED` | `instant_refund_enabled` is off and you sent `refund_type=INSTANT` | Drop `refund_type` (use standard) or enable instant in dashboard. |
| 404  | `order_not_found`     | `order_id` doesn't exist for this merchant                         | Verify the ID.                                                    |

## Implementation Checklist for AI

- [ ] Confirm `merchant-config.yml`'s `refunds_in_dashboard_enabled` is `true`. If `unknown`, ask the merchant.
- [ ] If using instant refund, confirm `instant_refund_enabled` is `true`. Otherwise default to standard refund (drop `refund_type`).
- [ ] Generate a `unique_request_id` and **persist it** before calling the API.
- [ ] Validate the requested refund amount against `order_status`'s `amount` minus any already-refunded amount.
- [ ] On HTTP 200, poll `order_status` to track the refund's lifecycle.
- [ ] **Do not** retry a refund call without the **same `unique_request_id`** — duplicate IDs are how the API protects against double refunds.

## Common AI Mistakes

### Field naming and gotchas

- `unique_request_id`, not `idempotency_key` or `request_id`. The other names are silently ignored, removing idempotency protection.
- Refund `amount` can be **less than** the order amount (partial refund). Multiple partial refunds against the same order are allowed up to the original amount.

### Validation rules

- Refunds against an `AUTHORIZED` (uncaptured) order should use the **void** flow, not refund. Void is non-monetary; refund is monetary and may incur fees.
- The `unique_request_id` must be unique per **refund attempt**, not per order. A single order with three partial refunds needs three distinct IDs.

### Doc-vs-code disagreements

- Some public docs describe a `refund_id` parameter. The canonical name is `unique_request_id`. The Juspay-issued refund ID is returned in the response as `refunds[].id`.
- The `refund_type` defaults to standard. Public docs sometimes imply instant is the default — it is not.

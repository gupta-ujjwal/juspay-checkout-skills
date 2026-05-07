---
name: error_codes
description: Common error codes returned by Juspay Checkout APIs and how to react
type: base
metadata:
  author: Juspay
  version: "0.1.0"
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/order--payment-api-integration/error-codes.md
---

## When to Apply

- Handling non-2xx responses from any Juspay Checkout endpoint.
- Mapping gateway responses into your application's error states.

## Response shape

All error responses follow this JSON shape:

```json
{
  "status": "ERROR",
  "error": true,
  "error_message": "Short human message.",
  "error_code": "<error_code>",
  "user_message": "Customer-safe explanation.",
  "error_info": {
    "code": "<unified_error_code>",
    "user_message": "...",
    "developer_message": "...",
    "fields": [{ "field_name": "...", "reason": "..." }]
  }
}
```

`error_code` is the legacy code; `error_info.code` is the unified code (newer). Both are present on most responses. Match on `error_info.code` if it is present, fall back to `error_code` otherwise.

## Error code reference

### 400 — Client errors

| Unified code          | Legacy `error_code`          | Cause                                                                                                                                              | Action                                                  |
| --------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `INVALID_INPUT`       | `invalid_request`            | Missing required field, bad format (e.g. malformed `order_id`), bad amount, type mismatch. The `error_info.fields` list names the offending field. | Fix the payload. Do not retry the same request.         |
| `INVALID_INPUT`       | `INVALID_MANDATE_MAX_AMOUNT` | Mandate `max_amount` outside the allowed range.                                                                                                    | Fix the value.                                          |
| `INVALID_INPUT`       | `INVALID_CUSTOMER_ID`        | `customer_id` does not exist or is malformed.                                                                                                      | Verify customer exists; create if needed.               |
| `FEATURE_NOT_ENABLED` | `FEATURE_NOT_ENABLED`        | A merchant-account flag required by this flow is disabled.                                                                                         | See `merchant_gates`. Contact Juspay support to enable. |

### 401 / 403 — Auth

| Unified code    | Cause                                                             | Action                             |
| --------------- | ----------------------------------------------------------------- | ---------------------------------- |
| `ACCESS_DENIED` | Invalid API key, wrong `x-merchantid`, expired client-auth token. | Fix credentials.                   |
| `BAD_ORIGIN`    | Source IP not on the merchant's allow-list.                       | Add IP to allow-list in dashboard. |

### 404 — Not found

| Cause                     | Action                       |
| ------------------------- | ---------------------------- |
| `order_id` does not exist | Verify the ID; do not retry. |

### 500 — Server errors

| Unified code               | Cause                                | Action                                                                            |
| -------------------------- | ------------------------------------ | --------------------------------------------------------------------------------- |
| `INTERNAL_SERVER_ERROR`    | Juspay-side issue.                   | Retry with exponential backoff (max 3 attempts). Log `x-response-id` for support. |
| `UPSTREAM_API_ERROR` (502) | Gateway returned an error to Juspay. | Retry; if persistent, the issue is at the gateway.                                |

## Idempotency

Most endpoints are **not** idempotent. Re-sending the same payload after a server error may cause double charges. Use these mechanisms:

| Operation                         | Idempotency mechanism                                                                                                                                                                   |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /orders`                    | The `order_id` is the idempotency key. Re-using returns `invalid_request`; do **not** generate a new ID and retry — first call `/order/status` to check whether the original succeeded. |
| `POST /orders/{order_id}/refunds` | Send `unique_request_id` on the body. Re-sending with the same value returns the original refund's status.                                                                              |
| `POST /txns`                      | The `txn_uuid` is the idempotency key, generated by Juspay on first call.                                                                                                               |

## Common AI Mistakes

### Field naming and gotchas

- `error_code` and `error_info.code` are not always identical strings. Match on the unified code (`error_info.code`) — it is the structured form.
- The `user_message` is meant to be safe to surface to end customers; `developer_message` and `error_message` are for logs and your dev console, not for end-user UI.

### Validation rules

- A 400 error with `INVALID_INPUT` is not retriable — re-sending the same payload returns the same error. Fix the payload.
- A 500 error is retriable, but bound your retries (max 3) and back off exponentially (1s → 2s → 4s).

### Doc-vs-code disagreements

- Some public docs use the term "API_ERROR" for a 500. The unified-error code in the response is `INTERNAL_SERVER_ERROR`. Match on the latter.
- Public docs list a curated subset of error codes. The full set is enumerated by `Euler.Common.Errors.PredefinedErrors` in the source — if you encounter a code not on this card, treat the HTTP status as authoritative and log the full response for review.

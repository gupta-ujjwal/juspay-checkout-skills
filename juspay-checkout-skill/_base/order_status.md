---
name: order_status
description: GET/POST /order/status — the authoritative source of truth for order and transaction state
type: base
metadata:
  author: Juspay
  version: "0.1.0"
  verified_against: euler-workspace-5 (2026-05-07 snapshot)
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/order--payment-api-integration/get-order-statusorderstatus.md
---

## When to Apply

- After receiving a webhook (treat the webhook as a **trigger**, not as truth — re-fetch status before acting).
- After redirecting back from a hosted-checkout / 3DS challenge (poll until terminal).
- Reconciling orders during a daily/hourly batch job.
- Investigating a single order's state during support.

> **This endpoint is the authoritative source.** Webhook payloads and SDK callbacks can be lost, replayed, or arrive out-of-order; the status endpoint is always reflective of current truth.

## Dependencies

- `auth_basic`
- `environments`
- `error_codes`

## Endpoints

| Environment | Method | Path                          | Notes                                       |
| ----------- | ------ | ----------------------------- | ------------------------------------------- |
| Sandbox     | GET    | `/order/status?order_id=<id>` | Lookup by `order_id` (most common)          |
| Sandbox     | POST   | `/order/status`               | Lookup with body (`order_id` or `txn_uuid`) |
| Production  | GET    | `/order/status?order_id=<id>` |                                             |
| Production  | POST   | `/order/status`               |                                             |

Both methods accept either `KeyAuth` (`auth_basic`) or `TokenAuth` (Bearer client-auth-token, used by SDK clients). Backend code should use `auth_basic`.

## Request

### Query parameters (GET) or body fields (POST)

| Field                               | Required                       | Notes                                                                             |
| ----------------------------------- | ------------------------------ | --------------------------------------------------------------------------------- |
| `order_id`                          | One of `order_id` / `txn_uuid` | Merchant-supplied order ID. Most common lookup.                                   |
| `txn_uuid`                          | One of `order_id` / `txn_uuid` | Juspay-issued transaction UUID. Use when the same `order_id` has been retried.    |
| `merchant_id`                       | No                             | Some integrations require this redundantly with `x-merchantid`; harmless to send. |
| `options.add_full_gateway_response` | No                             | `true`/`false`. When true, response includes the raw gateway response (verbose).  |
| `options.add_full_risk_response`    | No                             | Includes the risk-engine response.                                                |
| `options.add_address`               | No                             | Includes address fields in the response.                                          |
| `options.trimmed_webhook_response`  | No                             | Returns the trimmed shape used in webhooks.                                       |

`options.*` keys are sent as flat form/query keys with the dot literally in the name (e.g. `options.add_full_gateway_response=true`).

### Sample request (GET)

```bash
curl -X GET "https://sandbox.juspay.in/order/status?order_id=ORDER_001" \
  -H "Authorization: Basic ${auth}" \
  -H "x-merchantid: ${merchant_id}"
```

## Response

JSON. Key fields:

| Field            | Type   | Notes                                                      |
| ---------------- | ------ | ---------------------------------------------------------- |
| `order_id`       | string | Echoes input.                                              |
| `id`             | string | Juspay-issued internal order ID (`ordeh_*`).               |
| `status`         | string | Current `OrderStatus` enum value (see state machine).      |
| `status_id`      | int    | Numeric encoding of `status`.                              |
| `txn_uuid`       | string | The Juspay-issued UUID for the most recent attempt.        |
| `txn_id`         | string | Merchant-visible transaction ID.                           |
| `amount`         | number | Order amount.                                              |
| `currency`       | string | ISO code.                                                  |
| `payment_method` | string | e.g. `CARD`, `WALLET`, `UPI`.                              |
| `gateway_id`     | int    | Numeric ID of the gateway that processed the txn.          |
| `payment`        | object | Method-specific details (card brand, last 4 digits, etc.). |
| `udf1`–`udf10`   | string | Echo of values supplied at order create.                   |

## State machine (`OrderStatus`)

The 22 possible status values, grouped by phase. Status numeric IDs are stable.

| Status                   | ID  | Terminal | Meaning                                                                      |
| ------------------------ | --- | -------- | ---------------------------------------------------------------------------- |
| `CREATED`                | 1   | No       | Order has been created; no payment attempt yet.                              |
| `NEW`                    | 10  | No       | Initial state after creation, slightly different lifecycle from CREATED.     |
| `PENDING_AUTHENTICATION` | 15  | No       | Waiting for the customer to complete 3DS / VBV / OTP.                        |
| `JUSPAY_DECLINED`        | 22  | Yes      | Juspay risk engine declined the txn before reaching the gateway.             |
| `AUTHENTICATION_FAILED`  | 26  | Yes      | Customer failed the 3DS / VBV challenge.                                     |
| `AUTHORIZATION_FAILED`   | 27  | Yes      | Gateway authorization step failed (insufficient funds, etc.).                |
| `AUTHORIZING`            | 28  | No       | Authorization in flight at the gateway.                                      |
| `COD_INITIATED`          | 29  | No       | Cash-on-delivery flow started.                                               |
| `AUTHORIZED`             | 30  | No       | Card authorized but not yet captured (only relevant if pre-auth flow).       |
| `SUCCESS`                | 30  | **Yes**  | Charged successfully (also encoded as `30`; canonical "money taken" status). |
| `VOIDED`                 | 31  | Yes      | Authorized txn voided (pre-auth not captured).                               |
| `VOID_INITIATED`         | 32  | No       | Void in flight.                                                              |
| `CAPTURE_INITIATED`      | 33  | No       | Capture in flight.                                                           |
| `CAPTURE_FAILED`         | 34  | Yes      | Capture attempt failed.                                                      |
| `VOID_FAILED`            | 35  | Yes      | Void attempt failed.                                                         |
| `AUTO_REFUNDED`          | n/a | Yes      | Auto-refund triggered (e.g. duplicate charge).                               |
| `PARTIAL_CHARGED`        | n/a | Yes      | Less than the full amount was charged.                                       |
| `TO_BE_CHARGED`          | n/a | No       | Scheduled future charge (mandate execution).                                 |
| `DECLINED`               | n/a | Yes      | Equivalent to `JUSPAY_DECLINED` for non-Juspay tenants.                      |
| `AUTO_VOIDED`            | n/a | Yes      | Auto-voided (e.g. on conflict resolution).                                   |
| `NOT_FOUND`              | 40  | n/a      | Returned when the order does not exist (also yields HTTP 404).               |
| `ERROR`                  | -1  | n/a      | Internal error fetching status; safe to retry.                               |

### Polling pattern

Treat anything other than the **Yes** entries above as non-terminal and poll. Recommended schedule:

- After 3DS redirect: poll every 3 seconds for the first 30 seconds, then every 10 seconds up to 2 minutes.
- After webhook trigger: a single status fetch, no polling — webhooks fire only on state changes that should already be terminal.

## Error Handling

See `error_codes`. Specific to this endpoint:

| HTTP | `error_code`            | Cause                                       | Action                       |
| ---- | ----------------------- | ------------------------------------------- | ---------------------------- |
| 404  | `order_not_found`       | `order_id` does not exist for this merchant | Don't retry — verify the ID. |
| 401  | `access_denied`         | Auth issue                                  | Fix credentials.             |
| 500  | `INTERNAL_SERVER_ERROR` | Juspay-side error                           | Retry with backoff.          |

## Common AI Mistakes

### Field naming and gotchas

- `SUCCESS` and `AUTHORIZED` both have `status_id = 30`. The string status is the discriminator; the numeric `status_id` is **not** uniquely reversible to a single status.
- `NOT_FOUND` is a status value, but the HTTP response for a missing order is also a 404. Read the body, don't infer from the HTTP code alone.

### Doc-vs-code disagreements

- Public docs list a smaller set of statuses than what the gateway can return. Trust this card's enum (verified against the source) over external lists.
- Some legacy docs treat the webhook payload as authoritative. It is not — it is informational. Always re-fetch via `/order/status` before acting on a state transition.

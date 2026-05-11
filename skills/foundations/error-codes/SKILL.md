---
name: error-codes
description: Consolidated catalogue of Juspay backend API error codes — what each one means, why it fires, and how to remediate. Generic across endpoints. Use when interpreting a 4xx/5xx response, debugging an integration failure, or wiring up alerting.
---

# Juspay error codes

A single catalogue of the error responses a merchant backend will see across Juspay's APIs. Per-card "Common errors" sections in api-reference cards list the **top-5 errors specific to that route**; this card is the canonical source for anything cross-cutting.

## When to use

You're seeing a non-2xx response (or a 200 with an error envelope) and want to know what happened. Or you're wiring up alerting and need the full code → meaning map.

## Prerequisites

- `foundations/authentication/` — most 401s trace to auth misconfiguration.

## Authentication / authorisation

| Status | Code            | Cause                                                                                                                       | Fix                                                                                                                                    |
| ------ | --------------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 401    | `access_denied` | `Authorization` header missing or malformed; API key not base64-encoded with the trailing `:`.                              | Encode the API key as `printf '%s:' "$API_KEY" \| base64`, send as `Authorization: Basic <result>`.                                    |
| 401    | _(unspecified)_ | `x-merchantid` header missing, or its value doesn't match the merchant the API key belongs to.                              | Send the merchant ID matching the API key. See `skills/SKILL.md` §"Common request headers".                                            |
| 401    | _(route-mix)_   | Mixing schemes — sending KeyAuth credentials to a `POST /v2/orders` route that expects SignatureAuth (or vice-versa).       | Look up the route's expected scheme in its api-reference card.                                                                         |
| 400    | _(unspecified)_ | `x-routing-id` missing on any route. Required across every Juspay backend API (session, order-status, refund, customer, …). | Send `x-routing-id` (typically the `customer_id`; fall back to `order_id` for guest). See `skills/SKILL.md` §"Common request headers". |

## Request body / validation

| Status | Code                               | Cause                                                                                                            | Fix                                                                                                                                       |
| ------ | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 400    | `mandatory.fields.missing`         | A required body field is absent. Generic message; the route's api-reference card lists which fields it requires. | Check the route's §"Required fields" / §"Conditionally required" tables.                                                                  |
| 400    | `invalid.amount`                   | `amount` is non-numeric, zero, or negative.                                                                      | Stringified decimal with two places, > 0.                                                                                                 |
| 400    | `invalid.amount.exceeded`          | Refund amount > order's unrefunded balance.                                                                      | Read `amount - amount_refunded` from `GET /orders/{order_id}` before issuing the refund.                                                  |
| 400    | `invalid.client.id`                | `payment_page_client_id` does not belong to the authenticating merchant (session route only).                    | Verify the dashboard's payment-page client ID matches the API key's merchant.                                                             |
| 400    | `PAYMENT_PAGE_CLIENT_ID_NOT_FOUND` | `payment_page_client_id` missing entirely on `POST /session`.                                                    | Send `payment_page_client_id` from the dashboard.                                                                                         |
| 400    | `CUSTOMER_ID_NOT_FOUND`            | `customer_id` missing on a `POST /session` request with `action="paymentManagement"` or a mandate flow.          | Send the merchant's `customer_id` — same one used with `POST /v2/customers/{merchantCustomerId}` (see `api-references/create-customer/`). |
| 400    | _(field-format)_                   | Email doesn't parse, mobile contains non-digits, etc.                                                            | Validate against the field's documented format.                                                                                           |

## Lookup / not-found

| Status | Code              | Cause                                                           | Fix                                                                              |
| ------ | ----------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 404    | `order_not_found` | The `{order_id}` doesn't exist for the authenticating merchant. | Verify the order was created with the same merchant credentials; check spelling. |
| 404    | _(NOT_FOUND)_     | Customer or refund target doesn't exist.                        | Verify the path-parameter ID.                                                    |

## Refunds

| Status | Code                                   | Cause                                                                    | Fix                                                                                                |
| ------ | -------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| 400    | `duplicate.call`                       | Refund with this `unique_request_id` already completed for this order.   | Use a fresh `unique_request_id` for a new refund. Replaying the same ID returns this error — safe. |
| 400    | `duplicate.call` (5-sec window)        | Concurrent refund with the same amount already in flight for this order. | Wait for the in-flight refund to settle (~5 s), then check `refunds[]` before retrying.            |
| 400    | `invalid.order.not_successful`         | Refunding an order whose `status` is not `CHARGED` or `PARTIAL_CHARGED`. | Wait for the order to reach a charged terminal state via webhook + `/order/status` reconciliation. |
| 400    | `request.exceeded`                     | More than 25 refund attempts on this order (default per-order cap).      | Contact Juspay support to raise the cap.                                                           |
| 400    | `"instant refund flag is not enabled"` | Merchant account's `enabledInstantRefund` flag is off.                   | Contact Juspay support to enable instant refund on the merchant account.                           |

## Server-side

| Status | Code        | Cause                  | Fix                                                                                 |
| ------ | ----------- | ---------------------- | ----------------------------------------------------------------------------------- |
| 500    | _(generic)_ | Juspay internal error. | Retry with backoff. If persistent, escalate via Juspay support with the request ID. |

## Pattern: how to read an error response

Juspay's error envelope typically carries:

```json
{
  "status": "error",
  "status_id": <numeric>,
  "error_code": "<code from tables above>",
  "error_message": "<human-readable message>"
}
```

Some routes wrap differently — `duplicate.call` may surface as a 400 with a richer body that includes the conflicting refund's metadata, for example. **Always check `error_code` and `error_message` together**; the message often disambiguates between two failure modes that share a code (e.g. the two `duplicate.call` cases above).

## Related skills

- `foundations/authentication/` — for 401s.
- `foundations/order-status-actions/` — for failure statuses (`AUTHORIZATION_FAILED`, etc.) that the order-status response carries, distinct from API error responses.
- Per-api-reference §"Common errors" — top-5 errors specific to each route.

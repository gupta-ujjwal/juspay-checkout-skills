---
name: order_create
description: POST /orders — create a new order, the precursor to any payment transaction
type: base
metadata:
  author: Juspay
  version: "0.1.0"
  verified_against: euler-workspace-5 (2026-05-07 snapshot)
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/order--payment-api-integration/create-order-apiorders.md
---

## When to Apply

- Creating an order before initiating any payment.
- Implementing a "checkout begins" flow on your backend.

## Dependencies

- `auth_basic`
- `environments`
- `error_codes`

## Endpoints

| Environment | Method | Path      |
| ----------- | ------ | --------- |
| Sandbox     | POST   | `/orders` |
| Production  | POST   | `/orders` |

## Request

### Headers

```
Authorization: Basic <base64(api_key + ':')>
x-merchantid: <merchant_id>
Content-Type: application/x-www-form-urlencoded
```

The canonical content type is **form-encoded**. The endpoint also accepts JSON, but form-encoded matches the request type most directly and is what most existing integrations send.

### Required fields

| Field         | Type   | Validation                                                                                                                                                      |
| ------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `order_id`    | string | Must begin with an alphanumeric character; may include `- _ ( ) { } + ~ . ` — no spaces. Unique per merchant. Reusing an `order_id` returns an error.           |
| `amount`      | string | Decimal string. Must be `> 0`. Restricted-mode merchants have an additional max-amount cap (configured per account).                                            |
| `currency`    | string | ISO 4217 three-letter code (e.g. `INR`, `USD`, `SGD`). Defaults to the merchant's configured default if omitted, but always send it explicitly.                 |
| `customer_id` | string | Required when the order is to be associated with a stored customer (which is the common path). May be omitted for guest checkouts where merchant policy allows. |

> The Haskell type `OrderCreateRequest` declares every field as `Maybe`. That is **not** the same as "optional" — required-ness is enforced by the request handler's validation logic, not by the type. Treat the four fields above as required.

### Optional fields (most-used)

| Field            | Type   | Notes                                                                                           |
| ---------------- | ------ | ----------------------------------------------------------------------------------------------- |
| `customer_email` | string | Required if you want Juspay to send transactional email.                                        |
| `customer_phone` | string | E.164 or local-format depending on country.                                                     |
| `description`    | string | Free-form, surfaced on hosted pages.                                                            |
| `return_url`     | string | Where the customer is redirected after the payment session ends. Required for hosted/SDK flows. |
| `product_id`     | string | Optional product reference for analytics / dashboards.                                          |
| `udf1`–`udf10`   | string | User-defined fields, surfaced in webhook and status responses unchanged.                        |
| `metaData`       | string | Stringified JSON for arbitrary metadata.                                                        |
| `gateway_id`     | string | Force a specific gateway. Omit unless your routing logic requires it.                           |
| `payment_filter` | string | JSON-encoded payment-method filter — show/hide methods on hosted page.                          |

### Address fields (optional)

`billing_address_*` and `shipping_address_*` follow a parallel naming scheme. Each address has 11 fields: `first_name`, `last_name`, `line1`, `line2`, `line3`, `city`, `state`, `country`, `postal_code`, `phone`, `country_code_iso`. `country_code_iso` defaults to `IND` if omitted.

Send addresses only if your gateway requires them (some 3DS / risk flows do).

### Mandate fields (optional)

If creating a mandate alongside the order, set `options_create_mandate=REQUIRED` and supply the `mandate_*` fields. See the (forthcoming) `mandates_registration` flow for the full set.

### Sample minimum payload

```bash
curl -X POST "https://sandbox.juspay.in/orders" \
  -H "Authorization: Basic ${auth}" \
  -H "x-merchantid: ${merchant_id}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "order_id=ORDER_$(date +%s)&amount=100.00&currency=INR&customer_id=cust_001"
```

## Response

The body is JSON. Key fields on success:

| Field           | Type   | Notes                                                                              |
| --------------- | ------ | ---------------------------------------------------------------------------------- |
| `order_id`      | string | Echoes the request `order_id`.                                                     |
| `id`            | string | Juspay-issued unique ID (`ordeh_*`).                                               |
| `status`        | string | One of the `OrderStatus` enum values. On creation: `NEW` (or `CREATED`).           |
| `status_id`     | int    | Numeric mirror of `status` — see `order_status`.                                   |
| `merchant_id`   | string | Echoes `x-merchantid`.                                                             |
| `amount`        | number | Numeric amount.                                                                    |
| `currency`      | string | ISO code.                                                                          |
| `payment_links` | object | URLs for payment links; populated when `options_get_payment_collection_link=true`. |
| `juspay`        | object | Internal references — order tokens, etc.                                           |

### Response headers

| Header             | Notes                                                      |
| ------------------ | ---------------------------------------------------------- |
| `x-response-id`    | Juspay request correlation ID. Log it with every response. |
| `x-jp-order-id`    | Juspay-issued internal order ID.                           |
| `x-jp-merchant-id` | Echoes the merchant ID.                                    |

## Error Handling

See `error_codes` for the full table. Common cases for this endpoint:

| HTTP | `error_code`            | Cause                                                     | Action                                  |
| ---- | ----------------------- | --------------------------------------------------------- | --------------------------------------- |
| 400  | `invalid_request`       | Missing required field, bad `order_id` format, bad amount | Fix the payload; do not retry blindly.  |
| 400  | `FEATURE_NOT_ENABLED`   | The endpoint requires a merchant-account flag that is off | Contact Juspay support; do not retry.   |
| 401  | `access_denied`         | Bad API key or wrong `x-merchantid`                       | Fix the credentials; do not retry.      |
| 500  | `INTERNAL_SERVER_ERROR` | Juspay-side issue                                         | Retry with exponential backoff (max 3). |

A **duplicate `order_id`** returns 400 with an `invalid_request` error. Do not retry the same `order_id` — generate a new one.

## Common AI Mistakes

### Field naming and gotchas

- Use `order_id` (snake_case), not `orderId`. The form encoder is strict.
- The `amount` field is a **string** in the request type, not a number. Send `"100.00"`, not `100.00`. The handler parses it; sending a JSON number works but the canonical form is string.
- `customer_id` is for an existing or to-be-created customer. If `create_customer=true`, supply customer details (email, phone) on this request and Juspay will create a customer record from them.

### Validation rules

- `order_id` regex: must start with an alphanumeric, then alphanumerics or `- _ ( ) { } + ~ . `. **No spaces, no slashes.**
- Restricted-mode merchants have a maximum order amount and a per-day order count cap. Exceeding either returns `invalid_request` with a message naming the limit.

### Doc-vs-code disagreements

- The public docs list ~40 fields; the request record has 100+ optional fields. Most are for product-specific flows (mandate, mutual fund, virtual account, payment collection links) that you only need if you opted into those products. If a field is not documented in the public guide for your product, you almost certainly do not need it.
- Public docs sometimes show `Content-Type: application/json`. Both work, but form-encoded is canonical and matches the validators.

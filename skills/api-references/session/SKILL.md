---
name: session
description: Create a Juspay HyperCheckout session — the single backend call that initialises an order and returns the SDK payload the merchant's frontend hands to Juspay's hosted checkout. Use when implementing the HyperCheckout backend integration on the merchant server, populating session request fields, or forwarding the response to the frontend SDK.
---

# Session API — `POST /session`

The single backend call HyperCheckout requires. The merchant's server posts order details to `/session`; Juspay creates (or links to) an order and returns an `sdk_payload` the merchant forwards to the frontend SDK to render the hosted payment page.

## When to use

You're implementing the HyperCheckout backend on the merchant server and need to start a payment. Read this card whenever you're constructing the `POST /session` request, populating its body, or shaping the response your server hands to the frontend.

## Prerequisites

- `foundations/authentication/` — KeyAuth scheme.
- An active Juspay merchant account with `payment_page_client_id` provisioned.

## Endpoint

```http
POST /session
```

Base URLs are listed in `skills/SKILL.md` §"Base URLs". JWE variant (`POST /v4/session`) exists for merchants on encrypted endpoints — gated by account-level encryption keys (`basiliskKeyId`), deferred to Phase 2 (see [`README.md`](../../../README.md) §"Phase 1 omissions").

## Authentication

Standard KeyAuth set: `Authorization` + `x-merchantid` + `x-routing-id` + `Content-Type: application/json`. The headers are documented once in `skills/SKILL.md` §"Common request headers"; this route does not deviate from the baseline.

## Request body

`POST /session` accepts JSON. The session call creates the order under the hood: pass `order_id` in the body and it's linked to a new order with the same details. There is no separate `POST /orders` call required before `/session` for the HyperCheckout flow.

### Required fields

| Field                    | Type                | Notes                                                                                                   |
| ------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------- |
| `order_id`               | string              | Merchant's unique order ID. Alphanumeric, ≤ 21 characters.                                              |
| `amount`                 | stringified decimal | Two decimal places, e.g. `"100.00"`. Rejection on absence: `"Mandatory fields are missing"`.            |
| `payment_page_client_id` | string              | Juspay-issued client ID for the merchant's payment page. Rejection: `PAYMENT_PAGE_CLIENT_ID_NOT_FOUND`. |

### Conditionally required

| Field         | Required when                                                                     | Notes                                                                                                                               |
| ------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `customer_id` | `action="paymentManagement"`, **or** the request enables a mandate flow (Phase 2) | Rejection: `CUSTOMER_ID_NOT_FOUND`. For regular `paymentPage` checkouts without mandates, the field is optional and can be omitted. |

### Optional fields

| Field                                  | Type   | Notes                                                                                                                               |
| -------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `action`                               | string | `"paymentPage"` (default) or `"paymentManagement"` (manage payment methods).                                                        |
| `currency`                             | string | Three-letter currency code (e.g. `SGD`, `INR`). **Defaults to `"INR"` if omitted** — set explicitly for non-IN markets.             |
| `return_url`                           | string | Fully qualified URL the customer is redirected to after payment. Omit and the SDK returns control to the merchant frontend instead. |
| `customer_email`                       | string | Customer email. Useful for receipts and risk scoring but not required.                                                              |
| `customer_phone`                       | string | Customer phone (no country-code prefix).                                                                                            |
| `description`                          | string | Order description shown on the hosted page (≤ 255 chars).                                                                           |
| `language`                             | string | `EN` / `TH` / `VI` / `ID` / `KO`. Default `EN`.                                                                                     |
| `first_name`, `last_name`              | string | Customer name fields.                                                                                                               |
| `udf1` … `udf10`                       | string | User-defined pass-through fields.                                                                                                   |
| `metadata.JUSPAY:gateway_reference_id` | string | Optional gateway reference.                                                                                                         |

### Out of scope for Phase 1

Mandate fields (`options.create_mandate`, `mandate.max_amount`, `mandate.start_date`, etc.) are accepted on the request but the mandate flow itself is silent-gated by per-gateway mandate config on the merchant account. Phase 2.

## Response

All response fields are nullable; the merchant backend should treat the absence of `sdk_payload` or `payment_links` as a request-construction error.

> **The session response carries two distinct handoff payloads, one per client platform:**
>
> - **Native apps (Android, iOS, React Native, Flutter, Capacitor, Cordova)** — forward the `sdk_payload` object to the frontend. The native SDK consumes it directly via its initialisation API. **Do not use `payment_links.web`** on native clients.
> - **Web / mobile-web (browser-rendered checkout)** — pass `payment_links.web` to the frontend; the browser navigates to (or iframes) the hosted payment page at that URL. The `sdk_payload.clientAuthToken` is still available for any backend-issued SDK calls the web flow makes, but the primary handoff is the link.
>
> The merchant backend's job is the same for both: do `POST /session`, hand the right field to the right client. Which field your frontend reads is your frontend's contract with this backend.

```json
{
  "status": "NEW",
  "id": "ordeh_xxxxxxxxxxxxxxxxxxxx",
  "order_id": "ord_001",
  "payment_links": {
    "web": "https://api.juspay.in/orders/ordeh_.../payment-page",
    "expiry": "2026-05-10T12:34:56Z",
    "deep_link": null
  },
  "sdk_payload": {
    "requestId": "12398b5571d74c3388a74004bc24370c",
    "service": "in.juspay.hyperpay",
    "payload": {
      "clientId": "yourClientId",
      "amount": "100.00",
      "merchantId": "yourMerchantId",
      "clientAuthToken": "tkn_...",
      "clientAuthTokenExpiry": "2026-05-10T12:49:56Z",
      "environment": "sandbox",
      "orderId": "ord_001"
    },
    "expiry": "2026-05-10T12:49:56Z",
    "currTime": "2026-05-10T12:34:56Z",
    "xRoutingId": "cust_001"
  },
  "order_expiry": "2026-05-10T13:04:56Z"
}
```

### Field reference

| Field                      | Type      | Meaning                                                                                                                                         |
| -------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `status`                   | string    | Order status at session-create time — typically `NEW`. Full status enum: see `api-references/order-status/`.                                    |
| `id`                       | string    | Juspay's internal order ID (`ordeh_*`).                                                                                                         |
| `order_id`                 | string    | The `order_id` from the request (echoed).                                                                                                       |
| `payment_links.web`        | string    | URL of the hosted payment page. **Hand to web / mobile-web clients** — the browser navigates here (or iframes it). Don't use on native clients. |
| `sdk_payload`              | object    | **Hand to native clients** (Android, iOS, RN, Flutter, etc.). Forward verbatim to the frontend; the native SDK consumes it. Fields below.       |
| `order_expiry`             | timestamp | When the session expires. After expiry, the merchant must `/session` again.                                                                     |
| `links`                    | object    | Auxiliary links (rare; mostly `null`).                                                                                                          |
| `payment_link_qr`          | string    | QR code for the payment link (if requested).                                                                                                    |
| `payment_gateway_response` | object    | Pre-populated gateway response (rare in HC; usually `null` until txn completes).                                                                |
| `base64_encoded_qr`        | string    | Base64 QR (alternative form).                                                                                                                   |

### `sdk_payload` shape

The merchant backend forwards the full `sdk_payload` object to the frontend; the SDK expects every field as transmitted.

| Field                           | Required | Notes                                                                              |
| ------------------------------- | -------- | ---------------------------------------------------------------------------------- |
| `requestId`                     | yes      | Per-session request identifier.                                                    |
| `service`                       | yes      | `"in.juspay.hyperpay"` for HyperCheckout.                                          |
| `payload.clientId`              | yes      | Merchant's `payment_page_client_id`.                                               |
| `payload.amount`                | yes      | Echoed from the request.                                                           |
| `payload.merchantId`            | yes      | Merchant's ID.                                                                     |
| `payload.clientAuthToken`       | yes      | TokenAuth bearer the SDK uses for its own follow-up calls. **15-minute lifetime.** |
| `payload.clientAuthTokenExpiry` | yes      | Token expiry timestamp.                                                            |
| `payload.environment`           | yes      | `"sandbox"` or `"production"`.                                                     |
| `payload.orderId`               | yes      | Echoed from the request.                                                           |
| `expiry`                        | optional | Session-payload expiry (mirror of `order_expiry`).                                 |
| `currTime`                      | optional | Server time at issue.                                                              |
| `xRoutingId`                    | optional | Echo of `x-routing-id` header.                                                     |

## Worked example

```bash
API_KEY="your_sandbox_api_key"
MERCHANT_ID="your_merchant_id"
CLIENT_ID="your_payment_page_client_id"
AUTH=$(printf '%s:' "$API_KEY" | base64)

curl -sSL -X POST "https://sandbox.juspay.in/session" \
  -H "Authorization: Basic $AUTH" \
  -H "x-merchantid: $MERCHANT_ID" \
  -H "x-routing-id: cust_001" \
  -H "Content-Type: application/json" \
  -d "$(cat <<JSON
{
  "order_id": "ord_001",
  "amount": "100.00",
  "currency": "SGD",
  "customer_id": "cust_001",
  "customer_email": "test@example.com",
  "customer_phone": "9876543210",
  "payment_page_client_id": "$CLIENT_ID",
  "action": "paymentPage",
  "return_url": "https://shop.merchant.com/payments/return",
  "description": "Order 001",
  "first_name": "John",
  "last_name": "Doe"
}
JSON
)"
```

The merchant's server forwards the entire `sdk_payload` field of the response to the frontend, which passes it to the Juspay SDK's `process()` call.

## Common errors

| Status | Code                       | Cause                                                                    | Fix                                               |
| ------ | -------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------- |
| 400    | `mandatory.fields.missing` | One or more required body fields absent.                                 | Send all 8 required fields; check spelling.       |
| 400    | `invalid.amount`           | `amount` is non-numeric, zero, or negative.                              | Stringified decimal with two places, > 0.         |
| 400    | `invalid.client.id`        | `payment_page_client_id` does not belong to the authenticating merchant. | Verify the dashboard's client-ID is the one used. |
| 401    | `access_denied`            | `Authorization` header missing or malformed.                             | Encode `printf '%s:' "$API_KEY" \| base64`.       |
| 401    | _(unspecified)_            | `x-merchantid` missing or doesn't match the API key's merchant.          | Send the merchant ID matching the API key.        |

## Related skills

- `foundations/authentication/` — auth scheme details.
- `foundations/webhooks-and-signatures/` — receiving the `ORDER_*` event after the SDK completes.
- `api-references/order-status/` (Phase 1B-HC) — reconcile final state via `GET /orders/{order_id}`.
- `api-references/refund-order/` (Phase 1B-HC) — refund the order if/when needed.
- `integrations/hyper-checkout/` (Phase 1C-HC, not yet authored) — the full backend sequence that calls this API.

---
name: auth_basic
description: Default S2S auth — HTTP Basic with merchant API key plus x-merchantid header
type: base
metadata:
  author: Juspay
  version: "0.1.0"
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/authentication/api-key-authentication.md
---

## When to Apply

- Making any server-to-server call to Juspay Checkout APIs from your backend.
- Implementing `POST /orders`, `GET /order/status`, `POST /orders/{order_id}/refunds`, `POST /txns`, customer/payment-method APIs, and most other endpoints under `https://api.juspay.in` (or `https://sandbox.juspay.in`).
- This is the default auth scheme. Use `auth_signature` only if your integration explicitly uses `/v2/orders`. Use `auth_jwe` only if your integration explicitly uses `/v4/*` endpoints.

## Dependencies

- `environments`

## Request

Two HTTP headers on every request:

```
Authorization: Basic <base64(<api_key> + ":")>
x-merchantid: <merchant_id>
```

| Header          | Format                                   | Notes                                                                                                |
| --------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `Authorization` | `Basic <base64-encoded api_key + colon>` | Note the **trailing colon after the api_key** before base64. The password half is empty.             |
| `x-merchantid`  | Merchant ID string                       | Lowercase header. The merchant's identifier (issued at onboarding), not the merchant's display name. |

The body's `Content-Type` depends on the endpoint:

- `POST /orders` — `application/x-www-form-urlencoded` (canonical).
- `POST /orders/{order_id}/refunds` — `application/json` or form-encoded.
- See each flow card for the correct `Content-Type`.

### Sample header (Bash, sandbox)

```bash
api_key='your_sandbox_api_key_here'
merchant_id='your_merchant_id'
auth=$(printf '%s' "${api_key}:" | base64)

curl -X POST "https://sandbox.juspay.in/orders" \
  -H "Authorization: Basic ${auth}" \
  -H "x-merchantid: ${merchant_id}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "order_id=ORDER_001&amount=100.00&currency=INR&customer_id=cust_001"
```

## Common AI Mistakes

### Field naming and gotchas

- **Do not** omit the trailing colon before base64 encoding the API key. The Basic auth spec requires `username:password`; the password is empty but the colon must be present, otherwise the gateway returns `401 access_denied`.
- **Do not** put the API key in the `x-merchantid` header. The API key is in `Authorization`; `x-merchantid` carries the merchant ID, which is a separate identifier.
- **Do not** use `X-MerchantId` or `X-Merchant-Id` — the header name is `x-merchantid` (one word, all lowercase per HTTP convention; the proxy is case-insensitive but matches the documented form to avoid surprises).

### Validation rules

- The API key is environment-scoped. Sandbox keys do not work in production and vice versa.
- API keys are not bearer tokens — there is no expiry, but they can be rotated from the Juspay merchant dashboard.

### Doc-vs-code disagreements

- Some older Juspay documentation describes the auth as "Bearer". That is incorrect for `KeyAuth`-routed endpoints — the scheme is HTTP Basic. The Bearer scheme is `TokenAuth` and applies only to short-lived client-auth tokens used by the SDK.

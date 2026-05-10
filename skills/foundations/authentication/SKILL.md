---
name: authentication
description: Attach the right authentication scheme to a Juspay backend API request. Use when constructing an HTTP request to a Juspay endpoint and you need to know which header/credentials to use, what format they take, and which scheme applies to which route. Covers KeyAuth (server-to-server), TokenAuth (SDK-issued client tokens), and SignatureAuth (RSA-signed requests).
---

# Authentication

Juspay's backend APIs accept credentials via three schemes that you'll meet in Phase 1 integrations. Pick the scheme that matches the route, attach the right header or query params, and proceed.

## When to use

Read this card whenever you're constructing a Juspay HTTP request and you don't yet know how to authenticate it. Every API-reference and integration card in this bank assumes you've understood this card.

## Prerequisites

- An active Juspay merchant account with API credentials provisioned via the dashboard.
- For TokenAuth-backed flows, the merchant's frontend will receive a short-lived `client_auth_token` from Juspay; the backend doesn't generate this token directly.

## Public base URLs

| Environment | Host                        |
| ----------- | --------------------------- |
| Sandbox     | `https://sandbox.juspay.in` |
| Production  | `https://api.juspay.in`     |

The internal Servant routes in `euler-workspace-5/` carry an `/ecr` prefix — the edge proxy strips it. Always use the public path in skill cards and integration code.

## The three schemes (Phase 1)

### KeyAuth — server-to-server merchant API

The default scheme for backend-only calls (`POST /orders`, `POST /session`, `POST /txns`, refunds, order-status, customer APIs, etc.).

#### Headers

```http
Authorization: Basic <base64(api_key + ":")>
x-merchantid: <merchant_id>
x-routing-id: <customer_id_or_order_id>
```

Three headers, all required on most KeyAuth-protected endpoints:

- **`Authorization`** — HTTP Basic with the API key as username and an empty password. The colon-suffixed empty password is mandatory.
- **`x-merchantid`** — your merchant ID from the dashboard. Required at the route handler layer (constructs `XMerchantId` for downstream context, e.g. `euler-api-order/src/Euler/Server.hs:6714`).
- **`x-routing-id`** — typically the customer ID; falls back to order ID for guest checkout. Enforced by the `withXRoutingId` middleware (`Server.hs:339`); used for routing/consistency across services.

The auth scheme proper reads only `Authorization` (see verification path below); `x-merchantid` and `x-routing-id` are route-level requirements layered on top. The auth check passes when only `Authorization` is sent, but downstream handlers and middleware reject the request without the other two. Both IN and SEA public docs uniformly require all three.

#### Verification path

- Authorization header parsed at `euler-webservice/src/Euler/WebService/Services/AuthService/Auth/AuthKeyService.hs:46-71`.
- API key extracted by stripping the `Basic` prefix and base64-decoding, then taking everything before the first `:` — see `extractApiKey` at `AuthKeyService.hs:93-94`.
- Merchant account looked up by API key at `AuthKeyService.hs:71` (`fetchMerchantAccountRecordUsingApiKey`).
- `x-routing-id` middleware enforced at `euler-api-order/src/Euler/Server.hs:339` (`withXRoutingId`).

#### Worked example (sandbox)

```bash
API_KEY="your_sandbox_api_key"
MERCHANT_ID="your_merchant_id"
CUSTOMER_ID="cust_001"
AUTH=$(printf '%s:' "$API_KEY" | base64)

curl -sSL -X POST "https://sandbox.juspay.in/session" \
  -H "Authorization: Basic $AUTH" \
  -H "x-merchantid: $MERCHANT_ID" \
  -H "x-routing-id: $CUSTOMER_ID" \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ord_001","amount":"100.00","customer_id":"cust_001","action":"paymentPage"}'
```

### TokenAuth — SDK-issued client tokens

Used for client-side calls the SDK makes after the backend has handed over a session. The backend never sends TokenAuth itself — it just sees `client_auth_token` round-trip from `POST /session` (or `POST /orders`) back to the frontend, which the SDK then attaches to its own requests.

#### Lifetime

- 15 minutes from issue. Configured at `euler-webservice/src/Euler/WebService/Config/Config.hs:1131` (`orderTokenExpiry = 900` seconds).
- After expiry, the SDK must re-fetch a fresh token via the merchant backend.

#### Field

The token is delivered to the SDK in the response body (commonly `juspay.client_auth_token` inside the order response, or as `payload.client_auth_token` in the session response).

#### Backend responsibility

Pass the token through to the frontend in the response your server sends back. Don't strip it, don't cache it server-side, don't reuse it across customers. The token is single-session.

#### Verification path

- Token-bearing body type at `euler-api-pre-txn/src/Euler/Servant/Auth/TokenAuth.hs:35` (`client_auth_token :: RP.ClientAuthToken`).
- Validated at `TokenAuth.hs:49-68` (instance `Authenticate TokenAuth`).

### SignatureAuth — RSA-signed requests

Used on `POST /v2/orders` and other signed-body endpoints. The merchant signs the request body with their private key; Juspay verifies with the merchant's public key (uploaded via dashboard, looked up by `merchant_key_id`).

#### Algorithm

RSA with PKCS#1 v1.5 padding. Verification at `euler-webservice/src/Euler/WebService/Services/AuthService/Auth/AuthSignatureService.hs:195-202` (`verifyRSASignaturePKCS15`).

#### Required parameters (querystring or form-encoded body)

| Field               | Meaning                                                                |
| ------------------- | ---------------------------------------------------------------------- |
| `signature`         | Base64-encoded RSA-PKCS#1.5 signature over `signature_payload`.        |
| `signature_payload` | The string that was signed (typically the canonicalised request body). |
| `merchant_key_id`   | Identifier for the merchant's uploaded public key.                     |

Field type at `euler-api-pre-txn/src/Euler/Servant/Auth/SignatureAuth.hs:24-37`. Public-key lookup at `AuthSignatureService.hs:180-189`.

#### Worked example

```python
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

private_key = serialization.load_pem_private_key(open("merchant.key", "rb").read(), password=None)
payload = "amount=100.00&currency=SGD&order_id=ord_001"
signature = private_key.sign(payload.encode(), padding.PKCS1v15(), hashes.SHA256())
sig_b64 = base64.b64encode(signature).decode()

# Send: POST /v2/orders?signature=<sig_b64>&signature_payload=<payload>&merchant_key_id=<key_id>
```

## Choosing a scheme

Each api-reference card declares the scheme its endpoint expects (Phase 1B-HC: `session/`, `order-status/`, `refund-order/`). The defaults across Phase 1:

- **KeyAuth** — server-to-server merchant-API calls (HyperCheckout's `POST /session`, `GET /orders/{order_id}`, refunds).
- **SignatureAuth** — `POST /v2/orders` and other RSA-signed-body endpoints.
- **TokenAuth** — never constructed by the backend; the SDK on the frontend uses it after the backend hands over `client_auth_token` from a `/session` or `/orders` response.

## Common errors

| Symptom                                       | Likely cause                                                                                         | Fix                                                                                                          |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `401 Unauthorized` on every request           | API key not base64-encoded with trailing `:` (the colon-empty-password is mandatory for HTTP Basic). | Encode `printf '%s:' "$API_KEY" \| base64`, not just `base64 <<< "$API_KEY"`.                                |
| `400 Bad Request` despite valid Authorization | Missing `x-merchantid` or `x-routing-id` header. The auth scheme passes; the route handler rejects.  | Always send all three headers (`Authorization`, `x-merchantid`, `x-routing-id`) on KeyAuth-protected routes. |
| `401` only on some routes                     | Mixing schemes — sending KeyAuth where SignatureAuth is required (or vice-versa).                    | Look up the route in its api-reference card and match the scheme.                                            |
| TokenAuth call returns `Token expired`        | Token older than 15 minutes.                                                                         | Backend issues a fresh token via `/session`; tokens are not refreshable.                                     |
| Signature verification fails on `/v2/orders`  | `signature_payload` doesn't match the bytes that were signed (encoding/whitespace difference).       | Sign the exact byte string you transmit; do not re-canonicalise after signing.                               |

## Out of scope for Phase 1

Two additional schemes exist in the source but are deferred:

- **JWEAuth** — encrypted bodies on `/v4/*` endpoints. Requires `basiliskKeyId` and `encryptionKeyIds` to be configured on the `MerchantAccount` (silent-gated; off by default). Decryption logic at `euler-webservice/src/Euler/WebService/Services/AuthService/Auth/JwtAuth.hs:196-212`.
- **CreditKeyAuth** — credit-line merchants only. Reads `Authorization` like KeyAuth plus an explicit `X-Merchant-Id` header, then validates against a Redis whitelist. Path at `euler-webservice/src/Euler/WebService/Services/AuthService/Auth/AuthCreditKeyService.hs:34-74`.

Both will be documented in Phase 2 once merchant-enablement gates land — see [`README.md`](../../../README.md) §"Phase 1 omissions".

## Related skills

- `foundations/webhooks-and-signatures/` — what to do with the events Juspay sends back to your server.
- `api-references/order-create/`, `session/`, `txns/`, `create-customer/` (Phase 1B) — per-API payload shapes; each declares the scheme it expects.
- Bank entry point: `skills/SKILL.md`.

---
name: auth_signature
description: Signature-authed variant for /v2/orders and similar endpoints
type: base
metadata:
  author: Juspay
  version: "0.1.0"
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/authentication/signature-authentication.md
---

## When to Apply

- Calling `POST /v2/orders` (signature-authed order create variant).
- Any endpoint whose Servant route declaration uses `SignatureAuth`.
- **Do not** use this scheme for the canonical `POST /orders` — that uses `auth_basic`.

## Dependencies

- `environments`

## Request

Authentication is provided via **query string parameters**, not headers:

| Query param         | Required | Purpose                                                       |
| ------------------- | -------- | ------------------------------------------------------------- |
| `signature`         | Yes      | The signature of the canonical payload.                       |
| `signature_payload` | Yes      | The canonical payload that was signed (string-encoded).       |
| `merchant_key_id`   | Yes      | The numeric ID of the merchant signing key, issued by Juspay. |
| `order_details`     | Yes      | The encrypted/encoded order data.                             |

The body itself contains the order data; the query string carries the signature material. See the public reference for the exact canonicalization rules — they are not yet stabilized in the public docs and the canonicalizer should be obtained from Juspay support if you need this scheme.

## Common AI Mistakes

### Field naming and gotchas

- `merchant_key_id` is **not** the merchant ID. It is the numeric identifier of a specific signing key registered for the merchant. A single merchant can have multiple key IDs (e.g. for rotation).
- The signature material lives in the query string, not the body. Do not put `signature` in the form body — the route's authentication middleware reads the query string.

### Doc-vs-code disagreements

- Public docs do not document this auth scheme as completely as `auth_basic`. If your integration does not specifically require `/v2/orders`, use `auth_basic` instead.

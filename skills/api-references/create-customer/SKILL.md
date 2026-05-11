---
name: create-customer
description: Create-or-fetch a Juspay customer record keyed by the merchant's own customer ID — the prerequisite for tokenization (saved cards), linked-wallet flows, subscription/mandate flows, and cross-session analytics (FRM, 3DS step-up history). Use when any of those capabilities matter; skip for pure guest one-shot checkouts.
---

# Create Customer API — `POST /v2/customers/{merchantCustomerId}`

Creates or fetches a Juspay customer record keyed by the **merchant's** customer ID. Idempotent: posting with a `merchantCustomerId` that already exists returns the existing record rather than creating a duplicate or rejecting.

## When to use

A Juspay customer record is the precondition for any capability that needs a persistent customer identity inside Juspay:

- **Tokenization / saved cards** — card-on-file flows. A card is tokenised against the customer for repeat use without re-entering details.
- **Linked-wallet flows** — wallet providers that link once and are charged repeatedly (e.g. Paytm-style linked wallets).
- **Subscription / mandate flows** — recurring billing (Phase 2; mandate setup uses the customer record as the mandate holder).
- **Cross-session analytics** — Juspay's Fraud Risk Management (FRM), 3DS step-up history, and similar analytics are **scoped by customer ID across sessions**. Without a customer record, each session is treated as anonymous and risk decisions can't draw on past behaviour.

For pure one-shot **guest checkouts** that don't need any of the above, skip this card. Issue `POST /session` without a `customer_id` and the hosted page treats the payment as anonymous.

Also use this card to **update** an existing customer's contact details — pass `update="true"` with the new field values.

## Prerequisites

- `foundations/authentication/` — KeyAuth scheme.
- The merchant has a customer-account model with a stable, opaque per-customer ID (the `merchantCustomerId` you pass in the URL).

## Endpoint

```http
POST /v2/customers/{merchantCustomerId}
```

Base URLs are listed in `skills/SKILL.md` §"Base URLs". The `{merchantCustomerId}` is the merchant's own customer identifier — opaque to Juspay; pick a stable scheme (UUID, hash of email, etc.) and reuse it across all calls referring to the same customer.

## Authentication

KeyAuth — `Authorization: Basic <base64(api_key + ":")>`. `Content-Type: application/json`. The three universal headers are required as documented in `skills/SKILL.md` §"Common request headers" — `x-routing-id` for this route is typically the same `merchantCustomerId` you're posting.

## Request body

All body fields are optional — the call works with an empty body and just the path-parameter `{merchantCustomerId}`. In practice you'll send the customer's contact details so Juspay can pre-fill the hosted page and tag risk events.

| Field                           | Type   | Notes                                                                                                                                                                     |
| ------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mobile_number`                 | string | Customer phone, digits only (no country-code prefix).                                                                                                                     |
| `mobile_country_code`           | string | E.g. `+91`, `+65`. Required if `mobile_number` is sent.                                                                                                                   |
| `email_address`                 | string | Customer email.                                                                                                                                                           |
| `first_name`                    | string | Customer first name.                                                                                                                                                      |
| `last_name`                     | string | Customer last name.                                                                                                                                                       |
| `extended_customer_id`          | string | Secondary customer identifier (rare; used for legacy migrations).                                                                                                         |
| `update`                        | string | Pass `"true"` to force-update an existing customer's fields. Default behaviour returns existing customer unchanged.                                                       |
| `options.get_client_auth_token` | string | Pass `"true"` to receive a `client_auth_token` in the response (typically used by SDK-led flows; HyperCheckout backend doesn't need this since `/session` re-issues one). |

## Response

```json
{
  "id": "cst_xxxxxxxxxxxxxxxxxxxx",
  "object": "customer",
  "object_reference_id": "merchant_cust_001",
  "mobile_country_code": "+91",
  "mobile_number": "9876543210",
  "email_address": "test@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_created": "2026-05-11T12:34:56Z",
  "last_updated": "2026-05-11T12:34:56Z",
  "juspay": {
    "client_auth_token": "tkn_...",
    "client_auth_token_expiry": "2026-05-11T12:49:56Z"
  }
}
```

| Field                           | Type      | Meaning                                                                                                                                                                                            |
| ------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                            | string    | Juspay's internal customer ID (`cst_*`). **Merchants don't need to persist this** — your own `merchantCustomerId` is the identity you'll pass on subsequent calls. The `cst_*` is internal trivia. |
| `object_reference_id`           | string    | Echo of `merchantCustomerId` from the URL — the merchant's own ID. Juspay uses this to resolve `customer_id` on subsequent `POST /session` calls.                                                  |
| `mobile_*`, `email_*`, names    | strings   | Echo of what was posted (or what was previously stored if the record already existed and `update` was not sent).                                                                                   |
| `date_created` / `last_updated` | timestamp | Record lifecycle.                                                                                                                                                                                  |
| `juspay.client_auth_token`      | string    | Optional 15-minute bearer token, present only when `options.get_client_auth_token=true` was sent. Forward to the frontend SDK if the SDK needs to call Juspay directly.                            |

## Worked example

```bash
API_KEY="your_sandbox_api_key"
MERCHANT_ID="your_merchant_id"
MERCHANT_CUSTOMER_ID="merchant_cust_001"
AUTH=$(printf '%s:' "$API_KEY" | base64)

curl -sSL -X POST "https://sandbox.juspay.in/v2/customers/$MERCHANT_CUSTOMER_ID" \
  -H "Authorization: Basic $AUTH" \
  -H "x-merchantid: $MERCHANT_ID" \
  -H "x-routing-id: $MERCHANT_CUSTOMER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_country_code": "+91",
    "mobile_number": "9876543210",
    "email_address": "test@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

The same call with the same `merchantCustomerId` is safe to replay — Juspay returns the existing customer rather than creating a duplicate. Use this property to retry on network failures without bookkeeping.

## Idempotency and identity

The path-parameter `{merchantCustomerId}` **is** the customer's identity from the integration's perspective. **Generate it once per real-world customer and persist it on the merchant side.** Same ID + different body fields → existing record returned, fields unchanged (unless `update=true`). Same ID + `update=true` → existing record updated with whatever body fields are present.

Do **not** mint a fresh `merchantCustomerId` on retry — that creates a duplicate Juspay customer record for the same human, and saved cards / linked wallets / analytics history end up split across two records.

You don't need to track Juspay's `cst_*` ID on your side. Subsequent calls (e.g. `POST /session` with `customer_id`) resolve against the `merchantCustomerId` you originally provided; Juspay handles the `cst_*` ↔ `merchantCustomerId` mapping internally.

## Common errors

| Status | Code                | Cause                                                               | Fix                                                                 |
| ------ | ------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 400    | Invalid body        | Malformed JSON or unexpected field types.                           | Validate against the field table above.                             |
| 400    | Mobile/email format | `mobile_number` contains non-digits, `email_address` doesn't parse. | Strip country-code prefix; validate email format before submitting. |
| 401    | `access_denied`     | `Authorization` or `x-merchantid` missing/wrong.                    | Re-check headers per `skills/SKILL.md` §"Common request headers".   |

## Related skills

- `foundations/authentication/` — auth scheme.
- `api-references/session/` — `POST /session` references the `customer_id` you create here as the `customer_id` body field for logged-in flows.
- `integrations/hyper-checkout/` — the orchestrator that sequences this call as Step 0 for logged-in HyperCheckout flows.

---
name: create-customer
description: Create-or-fetch a Juspay customer record for a logged-in merchant customer — the prerequisite for any HyperCheckout flow that needs saved payment methods (saved cards, saved wallets) scoped to that customer. Use when implementing a logged-in checkout, registering a new merchant customer with Juspay, or fetching an existing customer's record before issuing a session.
---

# Create Customer API — `POST /v2/customers/{merchantCustomerId}`

Creates or fetches a Juspay customer record keyed by the **merchant's** customer ID. Idempotent: posting with a `merchantCustomerId` that already exists returns the existing record rather than creating a duplicate or rejecting.

## When to use

You need a Juspay-side customer to scope saved payment methods to:

- **Logged-in HyperCheckout flow** — the customer has an account on the merchant side and wants to reuse saved cards/wallets across sessions. Call this card before `POST /session`, then pass the same `customer_id` to the session.
- **Customer enrolment** — a new merchant signup, where you want a Juspay customer ready for the first payment.
- **Customer update** — the merchant has new contact details; passing `update=true` refreshes the existing record.

**For guest checkouts**, skip this card entirely. Issue `POST /session` without a `customer_id` and the hosted page treats the payment as one-off.

## Prerequisites

- `foundations/authentication/` — KeyAuth scheme.
- The merchant has a customer-account model with a stable, opaque per-customer ID (the `merchantCustomerId` you pass in the URL).

## Endpoint

```http
POST /v2/customers/{merchantCustomerId}
```

Base URLs are listed in `skills/SKILL.md` §"Base URLs". The `{merchantCustomerId}` is the merchant's own customer identifier — opaque to Juspay; pick a stable scheme (UUID, hash of email, etc.) and reuse it across all calls referring to the same customer.

## Authentication

Standard KeyAuth set: `Authorization` + `x-merchantid` + `x-routing-id` + `Content-Type: application/json`. The headers are documented once in `skills/SKILL.md` §"Common request headers"; this route does not deviate from the baseline. `x-routing-id` for this route is typically the same `merchantCustomerId` you're posting.

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

| Field                           | Type      | Meaning                                                                                                                                                                 |
| ------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                            | string    | Juspay's internal customer ID (`cst_*`). Persist this server-side; Juspay uses it internally to scope saved PMs.                                                        |
| `object_reference_id`           | string    | Echo of `merchantCustomerId` from the URL — the merchant's own ID.                                                                                                      |
| `mobile_*`, `email_*`, names    | strings   | Echo of what was posted (or what was previously stored if the record already existed and `update` was not sent).                                                        |
| `date_created` / `last_updated` | timestamp | Record lifecycle.                                                                                                                                                       |
| `juspay.client_auth_token`      | string    | Optional 15-minute bearer token, present only when `options.get_client_auth_token=true` was sent. Forward to the frontend SDK if the SDK needs to call Juspay directly. |

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

## Idempotency

The path-parameter `{merchantCustomerId}` is the dedup key. **Generate it once per merchant customer and persist it server-side.** Same ID + different body fields → existing record returned, fields unchanged (unless `update=true`). Same ID + `update=true` → existing record updated with whatever body fields are present.

Do **not** mint a fresh `merchantCustomerId` on retry — that creates a duplicate Juspay customer record with the same human customer, and you'll lose the saved-PM scoping benefit (saved cards live under one specific `cst_*`).

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

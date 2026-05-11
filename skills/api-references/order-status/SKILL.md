---
name: order-status
description: Fetch the authoritative state of a Juspay order — what the merchant calls after a webhook arrives or to reconcile state on its own cadence. Use when implementing the post-payment status check, polling for order state, or interpreting webhook events against ground truth.
---

# Order Status API — `GET /orders/{order_id}`

The **authoritative** read of order state. Webhooks tell you _something happened_; this call tells you _what is true now_. The merchant backend should treat the `/orders/{order_id}` response as ground truth and not the webhook body — Juspay's architecture guarantees this is the source of record (`docs/framework.md` and `architecture.md` cited).

## When to use

You need to know the current state of an order:

- After receiving a webhook (the recommended reconciliation pattern — see `foundations/webhooks-and-signatures/`).
- Polling on your own cadence (e.g. payment-link timeout flows).
- Showing a customer their final receipt after the SDK redirects back.

Do **not** trust the webhook body's `content.order` snapshot as final state — it's an event-time snapshot and may be redelivered or out-of-order.

## Prerequisites

- `foundations/authentication/` — KeyAuth scheme.
- An `order_id` already created (typically via `api-references/session/` for HyperCheckout merchants).

## Endpoint

```
GET /orders/{order_id}
```

Base URLs are listed in `skills/SKILL.md` §"Base URLs". The `{order_id}` is the merchant's `order_id` from session/order create. Use the path-parameter form on new integrations.

JWE variant (`GET /v4/order-status`) for merchants on encrypted endpoints — gated by account-level encryption keys (`basiliskKeyId`), deferred to Phase 2. Do **not** use the legacy `/orderStatus?order_id=` query-param form on new integrations — it exists for backward-compat with older merchants only.

## Authentication

KeyAuth, with two additional required headers:

```http
Authorization: Basic <base64(api_key + ":")>
x-merchantid: <merchant_id>
x-routing-id: <customer_id_or_order_id>
```

`x-routing-id` should match what the order/session was created with (typically the `customer_id`); falls back to the `order_id` for guest checkout. `version: YYYY-MM-DD` is required for new integrations — see `foundations/authentication/`.

## Query parameters

| Parameter                           | Required | Notes                                                                                                                                       |
| ----------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `options.add_full_gateway_response` | optional | `true` to include the full upstream gateway response object in `payment_gateway_response`. Increases payload size; use only when debugging. |

## Response

The order-status response has 80+ fields (most nullable). Each one of: order identification, money amounts, customer details, status, payment-method specifics, refund history, gateway response, EMI/mandate/offer/risk auxiliaries.

> **The tables below show a curated subset** — the fields a HyperCheckout backend agent typically needs. Other fields exist in the response (`mandate`, `metadata`, `chargebacks`, `risk`, `risk_checks`, `offers`, `emi_details`, `installment_plan_block`, `notification`, `additional_info`, `txn_additional_info`, `next_action`, `actions`, `pki_bind_details`, `card_present_payment_details`, etc.) and will appear in real responses. Consult the public order-status API reference for the full type when you need a field not listed here.

### Identification and amounts

| Field              | Type      | Notes                                   |
| ------------------ | --------- | --------------------------------------- |
| `id`               | string    | Juspay's internal order ID (`ordeh_*`). |
| `order_id`         | string    | Merchant's order ID.                    |
| `merchant_id`      | string    | Merchant's ID.                          |
| `amount`           | number    | Order amount.                           |
| `currency`         | string    | Currency code.                          |
| `amount_refunded`  | number    | Cumulative refunded amount.             |
| `effective_amount` | number    | Amount minus refunds (net charged).     |
| `paid_amount`      | number    | Amount actually captured.               |
| `date_created`     | timestamp | Creation time (ISO 8601 / local).       |
| `last_updated`     | timestamp | Last state mutation.                    |

### Customer

| Field                         | Type   | Notes                      |
| ----------------------------- | ------ | -------------------------- |
| `customer_id`                 | string | Merchant's customer ID.    |
| `customer_email`              | string | Customer email.            |
| `customer_phone`              | string | Customer phone.            |
| `customer_phone_country_code` | string | Country code (e.g. `+91`). |

### Status

| Field                 | Type      | Notes                                                                                  |
| --------------------- | --------- | -------------------------------------------------------------------------------------- |
| `status`              | enum      | See "Status values" below. The single most important field for backend reconciliation. |
| `status_id`           | int       | Numeric status ID; mirrors `status`.                                                   |
| `refunded`            | bool      | `true` once `amount_refunded == amount`.                                               |
| `refund_supported`    | bool      | `false` after `last_date_to_refund` passes.                                            |
| `last_date_to_refund` | timestamp | Beyond this, `POST /orders/{order_id}/refunds` will reject.                            |

### Status values

The `status` enum has **23 values total**.

> **Subset shown below.** The 12 wire values an agent will commonly receive on a HyperCheckout integration. The other 11 (`AUTHORIZING`, `CAPTURE_FAILED`, `CAPTURE_INITIATED`, `CREATED`, `ERROR`, `MERCHANT_VOIDED`, `DECLINED`, `AUTO_VOIDED`, `VOID_FAILED`, `VOID_INITIATED`, `NOT_FOUND`) **will arrive in production** for gateway edge cases, pre-auth flows, and merchant-side voids. Treat any unknown status as terminal-uncertain: do not assume success or failure; call `GET /orders/{order_id}` again or escalate.

| Wire value              | Meaning                                                                     |
| ----------------------- | --------------------------------------------------------------------------- |
| `NEW`                   | Order created, no payment attempt yet.                                      |
| `PENDING_VBV`           | Payment in progress, awaiting customer authentication (3DS, etc.).          |
| `AUTHORIZED`            | Payment authorised; for pre-auth flows, capture is the next step (Phase 2). |
| `CHARGED`               | **Terminal success.** Funds captured. The merchant should fulfill.          |
| `AUTHORIZATION_FAILED`  | Bank/issuer declined the authorisation.                                     |
| `AUTHENTICATION_FAILED` | Customer failed 3DS / OTP / equivalent.                                     |
| `JUSPAY_DECLINED`       | Juspay's risk engine declined the transaction.                              |
| `PARTIAL_CHARGED`       | Partial capture (split-tender or pre-auth partial).                         |
| `AUTO_REFUNDED`         | Juspay refunded the txn automatically (conflict resolution).                |
| `VOIDED`                | Pre-auth voided (Phase 2 flow).                                             |
| `COD_INITIATED`         | COD flow started; settlement happens out-of-band.                           |
| `TO_BE_CHARGED`         | Mandate / scheduled flow (Phase 2).                                         |

### Transaction details

| Field                      | Type   | Notes                                                                            |
| -------------------------- | ------ | -------------------------------------------------------------------------------- |
| `txn_id`                   | string | Latest transaction's ID at the gateway.                                          |
| `txn_uuid`                 | string | Juspay's UUID for the latest transaction.                                        |
| `payment_method_type`      | enum   | `CARD`, `NB`, `WALLET`, `UPI`, `CONSUMER_FINANCE`.                               |
| `payment_method`           | string | Specific method (e.g. `VISA`, `MASTERCARD`, `gpay`).                             |
| `auth_type`                | string | `THREE_DS`, `OTP`, `VIES`.                                                       |
| `gateway_id`               | int    | Internal gateway identifier.                                                     |
| `gateway_reference_id`     | any    | Gateway-specific ref (string or int depending on gateway).                       |
| `txn_detail`               | object | Full transaction detail; see `D.TxnDetail`.                                      |
| `payment_gateway_response` | object | Gateway response (only populated with `options.add_full_gateway_response=true`). |

### Cards / UPI

| Field               | Type   | Notes                                                                                                                                         |
| ------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `card`              | object | Card details — `last_four_digits`, `card_brand`, `card_type`, `expiry_year`, `expiry_month`, `card_isin`, `using_saved_card`, etc. (`D.Card`) |
| `payer_vpa`         | string | UPI VPA (when payment method is UPI).                                                                                                         |
| `payer_app_name`    | string | UPI app used.                                                                                                                                 |
| `upi.txn_flow_type` | string | `COLLECT` / `INTENT`.                                                                                                                         |

### Refunds (per-refund records)

`refunds` is an optional array — present when the order has been refunded (fully or partially). Each entry has these fields:

| Field               | Type      | Notes                                                             |
| ------------------- | --------- | ----------------------------------------------------------------- |
| `id`                | string    | Juspay's internal refund ID.                                      |
| `unique_request_id` | string    | Echoed from the merchant's refund request — your idempotency key. |
| `amount`            | number    | Refund amount.                                                    |
| `status`            | enum      | `PENDING` / `SUCCESS` / `FAILURE` / `MANUAL_REVIEW`.              |
| `created`           | timestamp | Refund initiation time.                                           |
| `gateway`           | string    | Which gateway processed.                                          |
| `epg_txn_id`        | string    | Gateway's refund transaction ID.                                  |
| `initiated_by`      | string    | `merchant` / `customer` / `juspay` (auto).                        |
| `error_message`     | string    | Populated on failure.                                             |
| `response_code`     | string    | Gateway response code on failure.                                 |
| `refund_arn`        | string    | Refund Acquirer Reference Number (when available).                |

### User-defined and metadata

| Field         | Type         | Notes                                               |
| ------------- | ------------ | --------------------------------------------------- |
| `udf`         | object / map | Echo of `udf1` … `udf10` from order/session create. |
| `metadata`    | string       | Echo of merchant-supplied metadata.                 |
| `description` | string       | Order description.                                  |
| `return_url`  | string       | The redirect URL that was set.                      |
| `product_id`  | string       | Optional product identifier.                        |

## Worked example

```bash
API_KEY="your_sandbox_api_key"
MERCHANT_ID="your_merchant_id"
ORDER_ID="ord_001"
AUTH=$(printf '%s:' "$API_KEY" | base64)

curl -sSL "https://sandbox.juspay.in/orders/$ORDER_ID" \
  -H "Authorization: Basic $AUTH" \
  -H "x-merchantid: $MERCHANT_ID" \
  -H "x-routing-id: cust_001"
```

The response `status` field tells you what to do next:

- `CHARGED` → fulfill the order.
- `PENDING_VBV`, `AUTHORIZING` → re-poll after a short delay; do not fulfill yet.
- `AUTHORIZATION_FAILED`, `AUTHENTICATION_FAILED`, `JUSPAY_DECLINED`, `DECLINED` → mark failed; show retry UX.
- `AUTO_REFUNDED` → the customer has been refunded by Juspay; show a corresponding message.

## Common errors

| Status | Code                       | Cause                                                                              | Fix                                                              |
| ------ | -------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 401    | `access_denied`            | `Authorization` header missing/wrong, or `x-merchantid` doesn't match the API key. | Re-encode credentials; verify the merchant ID.                   |
| 404    | `order_not_found`          | `{order_id}` not found for this merchant.                                          | Verify the order was created with the same merchant credentials. |
| 400    | `mandatory.fields.missing` | `order_id` path-param missing (shouldn't happen on a valid URL).                   | Construct the URL with `order_id` properly URL-encoded.          |

## Related skills

- `foundations/authentication/` — auth scheme.
- `foundations/webhooks-and-signatures/` — receive event hints; reconcile via this card.
- `api-references/session/` — creates the `order_id` you query here.
- `api-references/refund-order/` — refund operations are reflected back into the `refunds[]` array of this response.
- `integrations/hyper-checkout/` (Phase 1C-HC, not yet authored) — orchestrator that sequences this call after webhooks.

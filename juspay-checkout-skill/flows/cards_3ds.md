---
name: cards_3ds
description: Card payment with 3D Secure authentication — most common card flow, supports challenge and frictionless paths
type: flow
applies_to: [ec-api]
metadata:
  author: Juspay
  version: "0.1.0"
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/order--payment-api-integration/payment-flows/card-payment-3ds.md
---

## When to Apply

- Implementing a card payment that supports 3D Secure (3DS / VBV / EMV 3DS) authentication.
- The default for Indian cards (RBI mandates 3DS) and most international cards under SCA.
- Supports both **challenge** path (customer redirected to issuer ACS) and **frictionless** path (no challenge, direct authorization).

> **EC-API path only (Phase 1).** HyperCheckout and EC-SDK adapters land in Phase 3 — the subsections below for those modes are forward-reference stubs, not yet usable. `applies_to` will widen as those subsections are populated.

## Merchant Enablement

This flow uses card-payment infrastructure that is on by default. Optional gates that affect behaviour:

- `mandatory_2fa` — when `true`, no-3DS attempts are rejected. This flow is unaffected (3DS is on).
- `save_card_before_auth_enabled` — required if you want to tokenize the card on this transaction. Silent failure if disabled.

Confirm `merchant-config.yml` before generating tokenization code. See `merchant_gates`.

## Dependencies

- `auth_basic`
- `environments`
- `order_create`
- `order_status`
- `error_codes`
- `merchant_gates`

## Execution Flow

1. **Create the order** via `order_create`. Capture `{{order_create.output.order_id}}` and Juspay's `id`.
2. **Initiate the txn** — the call differs per integration mode (see subsections below). The response will indicate whether 3DS is required (`PENDING_AUTHENTICATION` status or a `next_step` redirect).
3. **Handle the 3DS challenge** — redirect the customer to the issuer ACS URL returned in the txn-init response, or render the embedded ACS form.
4. **Customer returns** to your `return_url` (or to an SDK callback). The return is informational only — do not act on it.
5. **Fetch authoritative status** via `order_status` (`/order/status?order_id=<id>`). Poll until terminal.
6. **Act on terminal status**: `SUCCESS` → fulfill the order; `AUTHORIZATION_FAILED` / `AUTHENTICATION_FAILED` / `JUSPAY_DECLINED` / `DECLINED` → mark the order failed and surface a customer-safe message.

## Endpoints (EC-API)

| Environment | Method | Path                       | Used in step |
| ----------- | ------ | -------------------------- | ------------ |
| Sandbox     | POST   | `/orders`                  | 1 (create)   |
| Sandbox     | POST   | `/txns`                    | 2 (initiate) |
| Sandbox     | GET    | `/order/status?order_id=…` | 5 (status)   |

(Production hosts swap `sandbox` for `api`.)

## Request

The request payload differs per integration mode. For step 1 (order create) refer to `order_create`; for step 5 (status fetch) refer to `order_status`. The mode-specific subsections below cover step 2 (txn initiation), where the payload differs most.

### EC-API integration

#### POST /txns — txn initiation

Headers:

```
Authorization: Basic <base64(api_key + ':')>
x-merchantid: <merchant_id>
Content-Type: application/x-www-form-urlencoded
```

Required body fields:

| Field                    | Type   | Notes                                                                                                               |
| ------------------------ | ------ | ------------------------------------------------------------------------------------------------------------------- |
| `order_id`               | string | The `order_id` from the order_create response.                                                                      |
| `merchant_id`            | string | Same as `x-merchantid`.                                                                                             |
| `payment_method_type`    | string | `CARD`.                                                                                                             |
| `payment_method`         | string | Card brand (`VISA`, `MASTERCARD`, `RUPAY`, etc.) — Juspay infers this from the BIN, but explicit value is accepted. |
| `card_number`            | string | PAN. PCI scope applies — only send from a PCI-compliant context.                                                    |
| `card_exp_month`         | string | 2-digit month, e.g. `08`.                                                                                           |
| `card_exp_year`          | string | 4-digit year, e.g. `2030`.                                                                                          |
| `card_security_code`     | string | CVV.                                                                                                                |
| `name_on_card`           | string | Cardholder name.                                                                                                    |
| `redirect_after_payment` | string | `true` (you'll handle a redirect back) or `false`.                                                                  |
| `format`                 | string | `json` (recommended) or `xml`.                                                                                      |

Optional:

| Field            | Notes                                                                                               |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| `auth_type`      | Force `THREE_DS` (default for 3DS-eligible cards) or `OTP` etc. Most integrations leave this unset. |
| `save_to_locker` | `true` to tokenize the card. Requires `save_card_before_auth_enabled`.                              |
| `is_emi`         | `true` for EMI; requires `installment_enabled`.                                                     |

#### Response (3DS challenge required)

```json
{
  "status": "PENDING_VBV",
  "txn_id": "merchant_id-ORDER_001-1",
  "txn_uuid": "abcdef123456",
  "payment": {
    "authentication": {
      "url": "https://acs.bank.example/3ds/...",
      "method": "GET"
    }
  },
  "order_id": "ORDER_001"
}
```

Redirect the browser to `payment.authentication.url`. After the customer completes the challenge, they are returned to the order's `return_url`.

#### Response (frictionless / direct authorization)

```json
{
  "status": "AUTHORIZED",
  "txn_id": "...",
  "order_id": "ORDER_001"
}
```

Skip the redirect; proceed to status polling.

### HyperCheckout integration

> **Phase 3.** Not yet covered in this skill bank. To use HyperCheckout, see the relevant Phase 3 platform card (Android / iOS / Web / React Native). At a high level: HyperCheckout wraps the `order_create` + `/session` + hosted-page flow into a single SDK call, with Juspay handling the 3DS redirect inside the hosted page.

### Express Checkout SDK integration

> **Phase 3.** Not yet covered. The SDK calls a token-authenticated variant of `/txns` and surfaces the 3DS challenge through a platform-native webview/redirect. The status fetch is the same `/order/status` endpoint.

## State machine (relevant slice of `OrderStatus`)

```
NEW
 │
 ├─→ PENDING_AUTHENTICATION  ──→  AUTHENTICATION_FAILED   (terminal failure)
 │              │
 │              └─→  AUTHORIZING  ──→  AUTHORIZATION_FAILED  (terminal failure)
 │                          │
 │                          └─→  SUCCESS  (terminal success — money taken)
 │
 └─→ JUSPAY_DECLINED  /  DECLINED   (risk decline — terminal failure, pre-gateway)
```

Note: `PENDING_VBV` (used in some legacy txn responses) maps to `PENDING_AUTHENTICATION` in the order status. Always poll `/order/status` rather than relying on the txn-create response status, since the latter is a snapshot of the moment the gateway accepted the request.

## Error Handling

See `error_codes`. Specific to this flow:

| HTTP | `error_code`            | Cause                                                      | Action                                                                                              |
| ---- | ----------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 400  | `invalid_request`       | Bad card number / expiry / CVV format                      | Validate client-side; do not retry blindly.                                                         |
| 400  | `FEATURE_NOT_ENABLED`   | Trying to tokenize without `save_card_before_auth_enabled` | See `merchant_gates`; suggest non-tokenize variant.                                                 |
| 402  | (gateway-mapped)        | Card declined (insufficient funds, etc.)                   | Surface customer-safe message; do not retry the same card.                                          |
| 500  | `INTERNAL_SERVER_ERROR` | Juspay-side                                                | Retry with backoff (max 3); poll `/order/status` afterward to confirm whether the txn went through. |

## Implementation Checklist for AI

- [ ] Confirm `merchant-config.yml` exists and the merchant has either filled in `save_card_before_auth_enabled` (if tokenizing) or you've set tokenization off in your code.
- [ ] Generate `order_create` call with at least `order_id`, `amount`, `currency`, `customer_id`, `return_url`.
- [ ] Generate `POST /txns` call with the required card fields above.
- [ ] Branch on the response: if `payment.authentication.url` present → redirect; else → poll status.
- [ ] Poll `/order/status` after the redirect and after the txn-create response to find the terminal state.
- [ ] On `SUCCESS`: fulfil the order. On any terminal failure: mark failed and surface `error_info.user_message`.
- [ ] **Do not** treat the txn-create response's `status` as terminal — re-fetch via `/order/status` always.
- [ ] **Do not** send card data through unsecured logs or analytics — PCI scope applies.

## Common AI Mistakes

### Field naming and gotchas

- `card_security_code`, not `cvv`. The latter is rejected.
- `card_exp_year` is a **4-digit** year (`2030`), not 2-digit.
- `payment_method_type` is the family (`CARD`, `WALLET`); `payment_method` is the brand (`VISA`).

### Validation rules

- A `PENDING_VBV` / `PENDING_AUTHENTICATION` response is **not** a failure — it means the customer needs to complete 3DS. Redirect them to `payment.authentication.url`.
- After the redirect, the customer's return URL receives only a hint. **Do not** trust the URL params (e.g. `status=success`) — re-fetch via `/order/status`.

### Doc-vs-code disagreements

- Public docs sometimes describe a single endpoint that does both order create and txn init in one call. That endpoint exists (`POST /txns/intent/create`) but the canonical two-step flow (`/orders` then `/txns`) is more debuggable and is what this card covers. The combined endpoint is appropriate for low-friction flows where you don't need separate order tracking.

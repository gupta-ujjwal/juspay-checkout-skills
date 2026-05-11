---
name: hyper-checkout
description: Integrate Juspay HyperCheckout end-to-end on the merchant's backend — the sequence of API calls and decisions that take a checkout from "customer clicked pay" to "merchant has authoritative final state". Use when the merchant has chosen the HyperCheckout (Juspay-hosted payment page) shape and is wiring it up server-side. Covers session creation, frontend handoff (native and web), webhook receipt, order-status reconciliation, and refunds.
---

# HyperCheckout — backend orchestrator

Juspay hosts the payment page; the merchant's backend issues a session, hands the SDK payload (or payment link) to the frontend, and reconciles state via webhooks + order-status calls. This card is the end-to-end recipe.

## When to use

The merchant has chosen **HyperCheckout** — they want Juspay to host the payment UI, render payment methods, and handle gateway interactions. The merchant's job is reduced to: issue an order/session on the backend, hand off to the frontend, receive callbacks, reconcile.

The alternatives — Express Checkout SDK (merchant hosts UI, Juspay's SDK handles payment-method rendering) and Express Checkout Backend (pure server-to-server, no SDK) — are Phase 2 and Phase 3 respectively. If the merchant's intent maps to either of those, stop reading this card and check `skills/SKILL.md` for the right entry point.

## Prerequisites

- `foundations/authentication/` — KeyAuth scheme.
- `foundations/webhooks-and-signatures/` — outbound webhook auth, retry semantics, event taxonomy.
- `api-references/session/` — `POST /session` payload and response.
- `api-references/order-status/` — `GET /orders/{order_id}` payload and status enum.
- `api-references/refund-order/` — `POST /orders/{order_id}/refunds`.
- `api-references/create-customer/` — `POST /v2/customers/{merchantCustomerId}` (logged-in flows only).
- An active Juspay merchant account with `payment_page_client_id` provisioned.
- A publicly reachable HTTPS endpoint registered as the merchant's webhook URL.

## Flow at a glance

```text
1. merchant backend  →  POST /session                                 →  Juspay
2. Juspay             →  sdk_payload + payment_links.web              →  merchant backend
3. merchant backend   →  hand off (native: sdk_payload; web: link)    →  merchant frontend
4. merchant frontend ←→  hosted payment page (Juspay drives UI)        ←→  Juspay
5. Juspay             →  webhook  AND/OR  return_url/handover         →  merchant
6. merchant backend   →  GET /orders/{order_id}                       →  Juspay
7. Juspay             →  authoritative order state                    →  merchant backend
8. merchant backend   →  act on status (fulfill / fail / re-poll)
```

Steps 1–3 are the outbound flow; steps 5–8 are the reconciliation loop. The hosted page (step 4) runs entirely on Juspay's side — the merchant's server is not on the critical path during payment itself.

## Backend sequence

Outbound flow plus reconciliation loop. Step 0 only applies to **logged-in customer flows**; guest checkouts skip straight to Step 1.

### Step 0 — Create-or-fetch the customer (logged-in flows only)

If the customer is logged into the merchant's app and you want them to see / use **saved payment methods** (saved cards, saved wallets), call `POST /v2/customers/{merchantCustomerId}` first. Pass the merchant's stable customer ID as the path parameter; Juspay creates the record on first call and returns the existing one on repeats. Persist the returned `id` (Juspay's `cst_*`) alongside your own customer record so the relationship is recoverable.

Skip this step entirely for **guest checkouts** — there's no customer record to associate with, and `POST /session` runs without `customer_id`.

Payload + response details: `api-references/create-customer/`.

### Step 1 — Collect order details

Server-side, gather what `POST /session` needs:

- The merchant's `order_id` (your idempotency key — see "Idempotency" below).
- `amount` (stringified decimal, two places) and `currency` (three-letter code — set explicitly, don't rely on the INR default).
- `payment_page_client_id` from the dashboard.
- `customer_id` **only if** Step 0 happened — i.e. logged-in flows that want saved-PM scoping. Guest checkouts omit it.
- Everything else (`customer_email`, `customer_phone`, `return_url`, `udf*`, etc.) is optional — see `api-references/session/` §"Request body" for the full requirement table.

### Step 2 — Call `POST /session`

Send the JSON request with the standard KeyAuth header set (see `skills/SKILL.md` §"Common request headers"). The response carries `sdk_payload`, `payment_links`, `order_expiry`. Persist `id` (Juspay's internal `ordeh_*`), `order_id`, and `order_expiry` on the merchant side — you'll need them in the reconciliation loop. The session call creates the underlying order; **there is no separate `POST /orders` step** for HyperCheckout.

Payload + response field details: `api-references/session/`.

### Step 3 — Hand off to the frontend

Send the right field to the right client. Both come from the same `POST /session` response:

| Client                                                           | Field to forward            | Why                                                                                                    |
| ---------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------ |
| Native (Android, iOS, React Native, Flutter, Capacitor, Cordova) | `sdk_payload` (full object) | The native SDK consumes this directly via its initialisation API. Do **not** send `payment_links.web`. |
| Web / mobile-web (browser)                                       | `payment_links.web`         | The browser navigates to (or iframes) the hosted payment page.                                         |

This is the same backend call (`POST /session`) for both — the merchant's frontend chooses which response field to read. Don't fork the backend by client type.

After handoff, the customer interacts with Juspay's hosted page; the merchant's server is **not on the critical path** during the payment itself. The next time the merchant hears anything is the webhook (step 4) or the customer's redirect to `return_url`.

### Step 4 — Receive the webhook

Implement the webhook receiver per `foundations/webhooks-and-signatures/`: HTTP Basic Auth verification, **persist → ack 200 → process asynchronously**, dedupe on `event.id`.

For HyperCheckout, the events you'll see in the happy path:

- `ORDER_SUCCEEDED` — payment captured.
- `ORDER_FAILED` — authorisation declined.
- Plus the refund family (`REFUND_SUCCEEDED`, `REFUND_FAILED`, `ORDER_REFUNDED`) when a refund completes asynchronously.

Treat the webhook body's `content.order` as an **event-time snapshot**, not as authoritative state. Step 5 is what gives you ground truth.

### Step 5 — Reconcile via `GET /orders/{order_id}`

Asynchronously (immediately on webhook receipt is fine, but don't block the ack), call `GET /orders/{order_id}` with KeyAuth + `x-merchantid` + `x-routing-id`. Treat the response's `status` field as authoritative.

Why this step exists rather than trusting the webhook directly:

- Webhooks may be redelivered, arrive out of order, or be missed entirely.
- The webhook body is an event-time snapshot; intervening events (auto-refund, void) may have superseded it.
- Order-status is the **only call Juspay guarantees as the source of record** for order state.

For the full response schema and the status enum, see `api-references/order-status/`. For reconciliation timing, see "Gotchas" below.

### Step 6 — Act on the final status

Map the order-status response to merchant-side behaviour:

| `status`                                                                       | Merchant action                                                                                                                                                                             |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CHARGED`                                                                      | Terminal success. Fulfill the order. Persist `txn_id`, `txn_uuid`, and `epg_txn_id` (from `txn_detail` / `payment_gateway_response`) for downstream gateway reconciliation.                 |
| `PENDING_VBV`, `AUTHORIZING`                                                   | Not terminal. Re-poll after a short delay (5–30 s) or wait for the next webhook. Do not fulfill.                                                                                            |
| `AUTHORIZED`                                                                   | For pre-auth flows (Phase 2), capture is the next step. Phase 1 HyperCheckout merchants typically don't use pre-auth.                                                                       |
| `AUTHORIZATION_FAILED`, `AUTHENTICATION_FAILED`, `JUSPAY_DECLINED`, `DECLINED` | Terminal failure. Mark failed; offer retry UX.                                                                                                                                              |
| `AUTO_REFUNDED`                                                                | Juspay refunded the customer automatically (conflict resolution). Notify the customer; do not fulfill.                                                                                      |
| `TO_BE_CHARGED`                                                                | Action required on the merchant side: Juspay has validated the order, now the merchant must initiate the charge transaction.                                                                |
| Anything else (`MERCHANT_VOIDED`, `CAPTURE_FAILED`, `ERROR`, …)                | Terminal-uncertain. Do not assume success or failure; re-poll `GET /orders/{order_id}` and/or escalate. See `api-references/order-status/` for the full enum and the unknown-status policy. |

## Refunds (sub-sequence)

When the merchant needs to refund a `CHARGED` order:

1. Generate a fresh `unique_request_id` (≤ 21 alphanumeric chars) per refund attempt and **persist it server-side** as your idempotency key. Same ID for the same order returns `duplicate.call` — that's the intended dedup behaviour.
2. `POST /orders/{order_id}/refunds` with KeyAuth + `x-merchantid` (note: refunds don't require `x-routing-id`) + the form-encoded body (`unique_request_id`, `amount`, optional fields). The response is the full order object with the new refund appended to `refunds[]` — same shape as `GET /orders/{order_id}`.
3. The new refund's `status` is `PENDING`. Subscribe to refund webhooks (`REFUND_SUCCEEDED`, `REFUND_FAILED`, `REFUND_MANUAL_REVIEW_NEEDED`); when one arrives, reconcile via `GET /orders/{order_id}` exactly as in step 5 above.

Payload, errors, and the `enabledInstantRefund` account-level gate: `api-references/refund-order/`.

## Gotchas

### Session expiry

`order_expiry` in the `/session` response (typically ~15 minutes from issue) bounds how long the SDK payload / payment link is valid. If the customer abandons checkout and returns later, **re-issue the session with the same `order_id`** — that links to the existing order rather than creating a new one. The `sdk_payload` and `clientAuthToken` are refreshed; the order persists.

### `order_id` is your idempotency key

Posting `POST /session` with an `order_id` that already exists links to that order rather than rejecting. This is by design — it lets clients retry on network failure without minting a new order. **Generate `order_id` once, persist it before the first `/session` call**, and reuse it across retries.

### Don't trust webhook body as terminal state

Already covered in step 5. Worth restating because the temptation to skip `GET /orders/{order_id}` is real when the webhook body looks complete. Resist it. The order-status call is cheap; missed/redelivered events are not.

### Webhook ack timing

Return `200` to Juspay's webhook POST **as soon as you've durably persisted the event** — not after processing. If you process before ack and processing fails, you've silently dropped an event. Juspay treats anything other than `200` as "not delivered" and retries.

### Clock skew on `order_expiry`

The expiry is a UTC timestamp. If the merchant's frontend computes expiry against local clock and the clock is skewed, the SDK may surface "session expired" prematurely or honor a stale session. Use UTC server time as the reference and check expiry server-side before re-handing off.

### Unknown status values

The order-status `status` enum has 23 values; 12 are documented in `api-references/order-status/`. The other 11 (`MERCHANT_VOIDED`, `CAPTURE_FAILED`, `CAPTURE_INITIATED`, `CREATED`, `ERROR`, `DECLINED`, `AUTO_VOIDED`, `VOID_FAILED`, `VOID_INITIATED`, `NOT_FOUND`, `AUTHORIZING`) arrive in production for gateway edge cases and pre-auth flows. **Treat any value not in the table above as terminal-uncertain** — re-poll `GET /orders/{order_id}` and/or escalate. Don't silently bucket unknown statuses into either success or failure.

## Testing checklist

A backend integration is "ready" when, against sandbox, the following all hold:

- [ ] `POST /session` returns a 200 with `sdk_payload`, `payment_links.web`, and `order_expiry` populated.
- [ ] Frontend handoff works for both native (consumes `sdk_payload`) and web (consumes `payment_links.web`) if both are supported.
- [ ] A successful sandbox payment fires `ORDER_SUCCEEDED`; the receiver verifies Basic Auth and returns 200.
- [ ] A failed sandbox payment fires `ORDER_FAILED`; same path.
- [ ] After each webhook, the merchant calls `GET /orders/{order_id}` and reads `status` — `CHARGED` / failure values match the webhook event.
- [ ] Re-issuing `POST /session` with the same `order_id` links to the existing order (response shows the same `id`) — confirms idempotency.
- [ ] A refund against a `CHARGED` order fires `REFUND_SUCCEEDED`; the same `unique_request_id` replayed returns `duplicate.call`.
- [ ] Webhook redelivery (force by returning 503 once, then 200) results in the merchant's handler running once after dedup — confirms idempotent processing.
- [ ] `GET /orders/{order_id}` after a failed authorisation shows the expected failure status (one of `AUTHORIZATION_FAILED`, `AUTHENTICATION_FAILED`, `JUSPAY_DECLINED`, `DECLINED`).

## Common errors (orchestrator-level)

| Symptom                                                                      | Cause                                                                     | Fix                                                                                                 |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Frontend SDK shows "session expired" before checkout completes               | `order_expiry` passed; SDK payload no longer valid                        | Re-issue `POST /session` with the same `order_id` to get a fresh `sdk_payload`.                     |
| Webhook arrives but `GET /orders/{order_id}` still shows the previous status | Reconciliation race — webhook fired before the order-status write settled | Re-poll after ~1–2 s; this lag is normally sub-second but spikes occasionally.                      |
| Different `id` returned across retries of `POST /session`                    | Different `order_id` passed each time (likely a fresh UUID per retry)     | Persist `order_id` server-side **before** the first `/session` call; reuse on retry.                |
| Refund initiated against a `PENDING_VBV` or `AUTHORIZING` order rejected     | Refunds only work on terminal-success orders                              | Wait for `CHARGED` (via webhook + `/order/status` reconciliation) before issuing the refund.        |
| Hosted page opens then closes immediately on web                             | Browser blocked the popup or iframe failed                                | Use `payment_links.web` as a top-level redirect rather than a popup; verify CSP / iframe-ancestors. |

## Related skills

- `foundations/authentication/` — auth scheme + route-level header rules.
- `foundations/webhooks-and-signatures/` — webhook receipt mechanics.
- `api-references/session/` — `POST /session` payload + response.
- `api-references/order-status/` — `GET /orders/{order_id}` payload + status enum.
- `api-references/refund-order/` — `POST /orders/{order_id}/refunds`.
- Bank entry point: `skills/SKILL.md`.

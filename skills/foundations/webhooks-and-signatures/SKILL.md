---
name: webhooks-and-signatures
description: Receive and process Juspay webhook callbacks server-side, and reconcile event state with the order-status API. Use when implementing a webhook receiver for Juspay payment events, configuring outbound webhook authentication, or deciding whether to trust an event payload as final state. Phase 1 covers unconditional webhook semantics; HMAC signature verification is deferred to Phase 2.
---

# Webhooks and signatures

Juspay notifies your server of payment events by POSTing JSON callbacks to a URL you've registered. This card covers how the delivery works, how to authenticate that a webhook came from Juspay, what the event taxonomy looks like, and — critically — why you should treat webhooks as event hints and confirm via `order-status` rather than trusting the webhook body as final state.

## When to use

Read this card when you're implementing the webhook receiver on the merchant's backend, or when you need to know what events Juspay emits and how to react to them. Every Phase 1 integration card assumes you've understood this.

## Prerequisites

- A publicly reachable HTTPS endpoint registered with Juspay (via dashboard) as your webhook URL.
- Optionally, HTTP Basic Auth credentials (username + password) configured on the dashboard so Juspay authenticates itself when calling your endpoint.
- `foundations/authentication/` understood — you'll need KeyAuth to call `GET /order/status` for reconciliation.

## Delivery contract

| Property        | Value                                                                              |
| --------------- | ---------------------------------------------------------------------------------- |
| Method          | `POST`                                                                             |
| Transport       | HTTPS only                                                                         |
| Body            | JSON                                                                               |
| Acknowledgement | HTTP `200 OK` from your endpoint                                                   |
| Retry           | Any non-`200` response (or timeout) → Juspay re-delivers                           |
| Deduplication   | Not guaranteed — under network conditions the same event may arrive more than once |

**Always return `200`** as soon as you've durably persisted the event for processing. Don't return `200` after running business logic — if your processing fails after the ack, you've silently dropped an event. The right pattern is: persist → ack → process asynchronously.

**Make your handler idempotent.** Use `event.id` (or the order/txn ID plus event_name) as a deduplication key.

## Outbound authentication (Juspay → your endpoint)

Juspay authenticates itself to your webhook endpoint using **HTTP Basic Auth** with credentials you've configured on the dashboard:

```http
Authorization: Basic <base64(username:password)>
```

Verify these credentials in your handler before doing anything else with the body. Reject `401` if they don't match — Juspay treats `401` as "not delivered" and will retry.

This is the only authentication channel between Juspay and your webhook endpoint that's enabled by default. Body-level signature verification is a separate, optional capability — see "Signature verification" below.

## Event payload shape

Standard webhooks (everything except mandate and notification webhooks) follow:

```json
{
  "id": "evt_<unique_id>",
  "date_created": "2026-05-10T12:34:56Z",
  "event_name": "ORDER_SUCCEEDED",
  "content": {
    "order": { "...order fields..." }
  }
}
```

Treat `content.order` as a snapshot at event time, not as the current state. For final state, call `GET /order/status` (see "Reconcile, don't trust" below).

## Event taxonomy

The canonical event names are defined at `euler-api-adapter/src/Adapter/API/Webhook/Types.hs:21-43`:

**Order lifecycle**
`ORDER_CREATED`, `ORDER_UPDATED`, `ORDER_SUCCEEDED`, `ORDER_FAILED`, `ORDER_AUTHORIZED`, `ORDER_PARTIAL_CHARGED`, `ORDER_VOIDED`, `ORDER_VOID_FAILED`, `ORDER_CAPTURE_FAILED`, `ORDER_COD_INITIATED`, `ORDER_TO_BE_CHARGED`

**Refund lifecycle**
`ORDER_REFUNDED`, `ORDER_REFUND_FAILED`, `REFUND_SUCCEEDED`, `REFUND_FAILED`, `AUTO_REFUND_SUCCEEDED`, `AUTO_REFUND_FAILED`, `REFUND_MANUAL_REVIEW_NEEDED`, `ORDER_AUTO_REFUNDED`

**Transaction lifecycle**
`TXN_CREATED`, `TRANSACTION_AUTHORIZED`, `TXN_CHARGED`

Additional event families exist for mandates and notifications and follow their own schemas; those land in Phase 2 alongside the mandate flow variant.

## Reconcile, don't trust

Juspay's architecture treats `GET /order/status` (and `POST /order/status`) as the **authoritative source of order state**. Webhooks are event hints — they tell you _something happened_, but the body may lag, may be redelivered, or may be missed entirely.

The recommended pattern:

1. Receive the webhook, verify Basic Auth, persist the event, return `200`.
2. Asynchronously, call `GET /order/status?order_id=<id>` (KeyAuth) and treat that response as ground truth.
3. Update your local order state from `/order/status`, not from the webhook body.

This pattern is robust to redelivery, ordering, and missed events.

## Signature verification — deferred to Phase 2

Juspay can additionally HMAC-sign webhook deliveries (and return-URL redirects) using the merchant's `paymentResponseHashKey`. The capability is **silent-gated** by `MerchantAccount.enablePaymentResponseHash` (`euler-db/src/Euler/DB/Storage/Types/MerchantAccount.hs:159-160`): when the gate is off, callbacks arrive unsigned; when it's on, an HMAC-SHA256 signature is attached.

Because the gate fails silently — a merchant whose gate is off will see "verification works" while actually receiving zero verification — Phase 1 deliberately does not document the verification mechanics. Doing so would imply the verification is unconditionally available, which it isn't.

This card will be extended in Phase 2 with:

- The exact signed-payload construction.
- The header/field where the signature lands for webhooks vs return-URL redirects.
- The gate prerequisite and how merchants enable it.

Until then: do not assume webhooks are signed; verify Basic Auth, reconcile via `/order/status`, and treat the webhook body as advisory.

See [`README.md`](../../../README.md) §"Phase 1 omissions" for the full deferral list.

## Common errors

| Symptom                                     | Likely cause                                                                                 | Fix                                                                                       |
| ------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Webhooks arrive but processing skips events | Returning `200` only after successful processing; transient failures look like ack to Juspay | Persist → ack → process. The ack is for "I received it", not "I handled it".              |
| Same order appears succeeded twice          | Handler not idempotent; redelivery hit it twice                                              | Dedupe on `event.id` or `(order_id, event_name)` before applying business logic.          |
| Order state in your DB lags Juspay          | Trusting webhook body as final state                                                         | After receiving the event, call `/order/status` and reconcile from there.                 |
| Juspay reports webhooks failing             | Endpoint returning non-`200`, or Basic Auth mismatch (`401`)                                 | Check your dashboard delivery log, verify Basic Auth credentials match what's configured. |

## Related skills

- `foundations/authentication/` — KeyAuth for the `/order/status` reconciliation call.
- `api-references/order-status/` (Phase 1B, not yet authored) — payload shape for the authoritative status check.
- Bank entry point: `skills/SKILL.md`.

Verified against `~/juspay/euler-workspace-5/`. Update this file whenever the source advances. The maintainer-discipline rules around verification live in [`conventions.md`](./conventions.md); this file holds only the data.

## Verified merchant-enablement gates

> Where these land in the bank — a `foundations/merchant-enablement/` skill, inline citations inside affected api-reference variants, or both — is a Phase 2 decision. Don't reference gates inside Phase 1 cards.

Verified against `euler-workspace-5/euler-db/src/Euler/DB/Storage/Types/MerchantAccount.hs` and gate-check sites in `euler-api-txns/oltp/src-generated/Product/OLTP/`.

| Flow / Feature                         | MerchantAccount field                                  | File:line                   | Failure mode                               |
| -------------------------------------- | ------------------------------------------------------ | --------------------------- | ------------------------------------------ |
| Pre-auth + capture (recapture)         | `enableRecapture`                                      | MerchantAccount.hs:106      | Loud — 400 from PreAuth.hs                 |
| Save card before auth (tokenization)   | `enableSaveCardBeforeAuth`                             | MerchantAccount.hs:157      | Silent — flow omitted                      |
| Reauthentication                       | `enableReauthentication`                               | MerchantAccount.hs:104      | Loud                                       |
| Reauthorization                        | `enableReauthorization`                                | MerchantAccount.hs:105      | Loud                                       |
| Return-URL HMAC signing                | `enablePaymentResponseHash` + `paymentResponseHashKey` | MerchantAccount.hs:159–160  | Silent — return-URL redirect unsigned      |
| Express Checkout SDK                   | `expressCheckoutEnabled`                               | MerchantAccount.hs:60       | Loud                                       |
| Inline Checkout                        | `inlineCheckoutEnabled`                                | MerchantAccount.hs:61       | Loud                                       |
| Whitelabel (HyperCheckout)             | `whitelabelEnabled`                                    | MerchantAccount.hs:111      | Loud                                       |
| Refunds via dashboard                  | `enableRefundsInDashboard`                             | MerchantAccount.hs:137      | Loud                                       |
| Instant refund                         | `enabledInstantRefund`                                 | MerchantAccount.hs:191      | Loud — 403 from Refund/Decider.hs          |
| Auto-refund on conflicts               | `autoRefundConflictTransactions`                       | MerchantAccount.hs:158      | Silent                                     |
| Auto-refund duplicate charges          | `autoRefundMultipleChargedTransactions`                | MerchantAccount.hs:192      | Silent                                     |
| Mandate auto-retry                     | `executeMandateAutoRetryEnabled`                       | MerchantAccount.hs:201      | Silent                                     |
| Mandate auto-revoke                    | `mandateAutoRevokeEnabled`                             | MerchantAccount.hs:209      | Silent                                     |
| Mandate per-gateway config             | `mandateConfig` (JSON)                                 | MerchantAccount.hs:216      | Silent — mandate flow disabled per gateway |
| EMI / installments                     | `installmentEnabled`                                   | MerchantAccount.hs:211      | Silent                                     |
| Offers engine                          | `offerEnabled`                                         | MerchantAccount.hs:208      | Silent                                     |
| OTP-based payments                     | `otpEnabled`                                           | MerchantAccount.hs:115      | Silent                                     |
| Reverse token                          | `reverseTokenEnabled`                                  | MerchantAccount.hs:116      | Silent                                     |
| 2FA mandatory                          | `mandatory2FA`                                         | MerchantAccount.hs:183      | Loud                                       |
| Unauthenticated order status           | `enableUnauthenticatedOrderStatusApi`                  | MerchantAccount.hs:180      | Loud                                       |
| Unauthenticated card add               | `enableUnauthenticatedCardAdd`                         | MerchantAccount.hs:181      | Loud                                       |
| External risk check                    | `enableExternalRiskCheck`                              | MerchantAccount.hs:161      | Silent                                     |
| Automatic retry                        | `enableAutomaticRetry`                                 | MerchantAccount.hs:154      | Silent                                     |
| Success-rate-based gateway elimination | `enableSuccessRateBasedGatewayElimination`             | MerchantAccount.hs:194      | Silent                                     |
| Gateway health-based routing           | `gatewayDecidedByHealthEnabled`                        | MerchantAccount.hs:120      | Silent                                     |
| JWE auth (request encryption)          | `basiliskKeyId`, `encryptionKeyIds`                    | MerchantAccount.hs:212–213  | Silent                                     |
| HTTP POST redirect (return_url)        | `redirectToMerchantWithHttpPost`                       | MerchantAccount.hs:185      | Silent                                     |
| Order notification (webhook delivery)  | `enableOrderNotification` + `webHookurl`               | MerchantAccount.hs:148, 150 | Silent                                     |
| Conflict status notification           | `enableConflictStatusNotification`                     | MerchantAccount.hs:168      | Silent                                     |
| Master kill-switch                     | `enabled`                                              | MerchantAccount.hs:204      | Loud                                       |

**Sub-merchant gates**:

- `MerchantGatewayAccount.disabled` (gateway-level)
- `MerchantGatewayAccount.supportedPaymentFlows` JSON (e.g. `DIRECT_DEBIT`, `V2_LINK_AND_PAY`, `CARD_MOTO`)
- `MerchantGatewayPaymentMethod.enabled` (per payment-method)
- `Feature` table (runtime kill-switch by name)

**Loud failures** throw explicit errors (refund disabled, CARD_MOTO not enabled, pre-auth not allowed). **Silent failures** just omit the feature from the response — these are the dangerous ones for AI agents because the integration "works" but quietly drops capability.

**Webhook outbound auth ≠ HMAC signing.** Outbound webhook delivery (Juspay → merchant endpoint) uses **HTTP Basic Auth** with merchant-configured username/password — that mechanism is not gated and is not HMAC. The "Return-URL HMAC signing" gate above governs only the return-URL signing path. See "Unverified / open questions" below for the webhook-body HMAC status.

## Merchant-facing endpoint inventory

From `euler-workspace-5` Servant/Wai route definitions. **Public paths** (after edge proxy strips `/ecr`).

### Order service (`euler-api-order/src/Euler/Server.hs:2444`)

**Merchant-facing routes** (a backend agent should call these):

- `POST /orders` — create order (KeyAuth, form-encoded canonical)
- `POST /orders/{order_id}` — update order
- `GET /orders/{order_id}` — **canonical order status; this is what a merchant calls** (`OrderStatusUrlCapture` at `Server.hs:2540`). Path-parameter form. KeyAuth + `x-merchantid` + `x-routing-id` headers.
- `POST /v4/orders` — JWE-encrypted order create
- `GET|POST /v4/order-status` — JWE-encrypted order status (`Server.hs:2513-2517`)
- `POST /session` — fetch session for payment page (also `/v4/session` JWE; `Server.hs:1975`, `2515`)
- `POST /txns/intent/create` — combined order+txn API
- `POST /v2/orders` — encrypted/signed variant (SignatureAuth)

**Internal / legacy routes** (do not surface in merchant-facing skill cards):

- `GET|POST /orderStatus?order_id=<id>` — legacy query-param order status (`Server.hs:2544-2550`). Predates the path-parameter canonical form; merchants on new integrations use `GET /orders/{order_id}`.
- `GET|POST /order/payment-status` — internal txn-level payment status (`Server.hs:2461-2463`). Authoritative status source per architecture.md, but **the merchant calls `GET /orders/{order_id}`**, which composes its response from this internal source. Listed here for architectural completeness only.

### Txn service (`euler-api-txns/src/Euler/API/Txns/Server.hs`)

- `POST /txns` — initiate txn (SDK / API)
- `POST /txns/continue` — continue (OTP)
- `GET /pay/next-step` — next step in flow
- `POST /txns/eligibility` — payment-method eligibility
- `POST /v2/txns/{txnUuid}/authenticate` — submit OTP
- `POST /v2/txns/{txnUuid}/authenticate/{challengeId}/resend` — resend OTP
- `POST|GET /v2/txns/{txnUuid}/capture` — pre-auth capture
- `POST|GET /v2/txns/{txnUuid}/void` — pre-auth void
- `PUT /txns/auth-modification` — modify auth amount
- `POST /orders/{order_id}/refunds` — refund
- `POST|GET /orders/txns/{txn_id}/refunds` — refund by txn
- `POST /mandates/{mandate_id}` — mandate execute (pay/revoke/pause)
- `GET /customers/{customer_id}/mandates` — list mandates

### Pre-txn service (`euler-api-pre-txn/apiTypes/src/Euler/App/Routes.hs`)

- `POST /v3/eligibility`, `POST /v5/eligibility`
- `GET /merchants/{merchantId}/paymentmethods`
- `POST /v2/emi/plans`, `POST /installments`
- `GET|POST|DELETE /merchants/{merchantId}/paymentmethods/saved`
- `POST /merchants/{merchantId}/lists/offers`

### Customer service (`euler-api-customer/src/Euler/Server.hs:246`)

- `POST /v2/customers/{merchantCustomerId}` — create/find
- `GET /customers/{merchantCustomerId}` — get
- `POST /customers/{customerId}` — update
- `POST|GET /customers/{customerId}/{bank-accounts|wallets|virtual-accounts}` — sub-resources
- `GET /customers/{customerId}/mandates` — list

### Auth schemes

- **KeyAuth** — `Authorization: Basic base64(api_key:)` plus required headers `x-merchantid` and `x-routing-id` on most routes
- **TokenAuth** — bearer-style `client_auth_token` (15-min lifetime, body/query field; SDK/client only — backends never construct this)
- **SignatureAuth** — querystring (`signature`, `signature_payload`, `merchant_key_id`)
- **JWEAuth** — encrypted bodies on `/v4/*` endpoints; reads `x-jp-merchant-id` / `x-merchant-id` / `x-merchantid` headers
- **CreditKeyAuth** — KeyAuth + `X-Merchant-Id` header + Redis whitelist; credit-line merchants only

**Header semantics under KeyAuth.** The auth scheme proper reads only `Authorization` (`euler-webservice/src/Euler/WebService/Services/AuthService/Auth/AuthKeyService.hs:46-71`). `x-merchantid` and `x-routing-id` are route-level requirements imposed by middleware (`withXRoutingId` at `euler-api-order/src/Euler/Server.hs:339`) and individual handlers (e.g. `Server.hs:6714` constructs `XMerchantId` from the header value for downstream context). The IN and SEA public docs uniformly require both headers on KeyAuth-protected endpoints; agents should always send them.

## Unverified / open questions

These items are _not_ verified against `euler-workspace-5/`. They are documented unknowns to be resolved before downstream cards rely on them; do not treat anything in this section as ground truth.

- **Webhook-body HMAC signing.** Only the return-URL signing path uses `paymentResponseHashKey` (`euler-api-order/src/Euler/Product/OLTP/Order/PaymentStatusHelpers.hs:54`). No webhook-body HMAC signing code path was located in this audit. If such a path exists (for example in a webhook-delivery worker or adapter that wasn't read), agents reading the bank may incorrectly conclude their webhooks are unsigned. Tracked in [#8](https://github.com/gupta-ujjwal/juspay-checkout-skills/issues/8) — to be resolved before Phase 2 webhook-verification cards ship.

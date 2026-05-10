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
| Webhook HMAC signing                   | `enablePaymentResponseHash` + `paymentResponseHashKey` | MerchantAccount.hs:159–160  | Silent — webhooks unsigned                 |
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

## Merchant-facing endpoint inventory

From `euler-workspace-5` Servant/Wai route definitions. **Public paths** (after edge proxy strips `/ecr`).

### Order service (`euler-api-order/src/Euler/Server.hs:2444`)

- `POST /orders` — create order (KeyAuth, form-encoded canonical)
- `POST /orders/{order_id}` — update order
- `GET /orders/{order_id}` — get order status
- `GET|POST /order/status` — order status (the **authoritative** status source per architecture.md)
- `POST /v4/orders` — JWE-encrypted order create
- `GET|POST /v4/order-status` — JWE order status
- `POST /session` — fetch session for payment page (also `/v4/session` JWE)
- `POST /txns/intent/create` — combined order+txn API
- `POST /v2/orders` — encrypted/signed variant (SignatureAuth)

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

- **KeyAuth** — `Authorization: Basic base64(api_key:)` plus `x-merchantid`
- **TokenAuth** — `Authorization: Bearer <client_auth_token>` (15-min lifetime, for SDK/client)
- **SignatureAuth** — querystring (`signature`, `signature_payload`, `merchant_key_id`)
- **JWEAuth** — encrypted bodies on `/v4/*` endpoints
- **CreditKeyAuth** — credit-line specific

---
name: merchant_gates
description: How to read merchant-config.yml and the merchant-account gating model that decides which flows are enabled
type: base
metadata:
  author: Juspay
  version: "0.1.0"
  verified_against: euler-workspace-5 (2026-05-07 snapshot)
references:
  - https://juspay.io/sea/docs/getting-started/merchant-account-configuration.md
---

## When to Apply

- **Before generating code for any flow card whose frontmatter declares it gated.** Almost every payment flow is gated by at least one merchant-account flag.
- When the merchant reports "the integration runs but feature X doesn't appear" — likely a silent-failure gate.

## Why gates matter

Juspay merchant accounts have ~30 boolean flags that control which flows are enabled. They split into two failure modes:

- **Loud gates** — when the gate is off, the API rejects the request with `FEATURE_NOT_ENABLED` (HTTP 400). Easy to detect.
- **Silent gates** — when the gate is off, the feature is **silently omitted** from the response. The API returns 200; the integration appears to work; but the gated capability quietly disappears.

Silent gates are the dangerous case for AI-generated code. You will not see an error; you will see a successful response with the wrong shape.

## Workflow rule

The merchant should keep a `merchant-config.yml` at the project root (copy `merchant-config.yml.example`). Each gate has one of three values:

- `true` — gate is enabled for this merchant. Generate code that uses the gated feature.
- `false` — gate is disabled. **Do not** generate code that depends on it. Either skip the feature or stop and tell the merchant the gate is required.
- `unknown` — value not yet confirmed. **Stop and ask the merchant** before generating code that depends on this gate.

When the value is `unknown`, ask in this form:

> This flow uses Juspay's `<feature_name>` capability, which is gated by the `<flag_name>` merchant-account flag (see Juspay merchant dashboard). Please confirm one of:
>
> - It is **enabled** — I'll proceed and update `merchant-config.yml`.
> - It is **disabled** — I'll suggest an alternative flow.
> - You're not sure — please contact Juspay support to confirm before I generate this code.

Update `merchant-config.yml` after the merchant confirms.

## Gate reference

The verified gates and their effects. The flow cards reference these by name.

### Loud failures (request rejected if disabled)

| `merchant-config.yml` key              | MerchantAccount flag                  | Used by flows                                        |
| -------------------------------------- | ------------------------------------- | ---------------------------------------------------- |
| `recapture_enabled`                    | `enableRecapture`                     | `cards_preauth_capture`                              |
| `reauthentication_enabled`             | `enableReauthentication`              | (advanced 3DS retries)                               |
| `reauthorization_enabled`              | `enableReauthorization`               | (extended-auth flows)                                |
| `express_checkout_enabled`             | `expressCheckoutEnabled`              | All EC-SDK platform integrations                     |
| `inline_checkout_enabled`              | `inlineCheckoutEnabled`               | Inline checkout                                      |
| `whitelabel_enabled`                   | `whitelabelEnabled`                   | All HyperCheckout platform integrations              |
| `refunds_in_dashboard_enabled`         | `enableRefundsInDashboard`            | `refund` (dashboard path)                            |
| `instant_refund_enabled`               | `enabledInstantRefund`                | `refund` (instant variant — returns 403 if disabled) |
| `mandatory_2fa`                        | `mandatory2FA`                        | All card flows when on; rejects no-3DS attempts      |
| `unauthenticated_order_status_enabled` | `enableUnauthenticatedOrderStatusApi` | Public-facing order status endpoint                  |
| `unauthenticated_card_add_enabled`     | `enableUnauthenticatedCardAdd`        | Save-card before login                               |

### Silent failures (feature dropped without error)

| `merchant-config.yml` key                   | MerchantAccount flag                                   | Used by flows                                                 |
| ------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| `save_card_before_auth_enabled`             | `enableSaveCardBeforeAuth`                             | Card tokenization in EC flows                                 |
| `payment_response_hash_enabled`             | `enablePaymentResponseHash` + `paymentResponseHashKey` | Webhook signing — without this, webhook payloads are unsigned |
| `auto_refund_conflict_transactions`         | `autoRefundConflictTransactions`                       | Conflict resolution                                           |
| `auto_refund_multiple_charged_transactions` | `autoRefundMultipleChargedTransactions`                | Duplicate-charge auto-refund                                  |
| `mandate_auto_retry_enabled`                | `executeMandateAutoRetryEnabled`                       | Mandate execution                                             |
| `mandate_auto_revoke_enabled`               | `mandateAutoRevokeEnabled`                             | Mandate lifecycle                                             |
| `installment_enabled`                       | `installmentEnabled`                                   | EMI / installments                                            |
| `offers_enabled`                            | `offerEnabled`                                         | Offers engine                                                 |
| `otp_enabled`                               | `otpEnabled`                                           | OTP flows                                                     |
| `external_risk_check_enabled`               | `enableExternalRiskCheck`                              | Risk integration                                              |
| `automatic_retry_enabled`                   | `enableAutomaticRetry`                                 | Retry engine                                                  |
| `gateway_health_routing_enabled`            | `gatewayDecidedByHealthEnabled`                        | Smart routing                                                 |
| `redirect_to_merchant_with_http_post`       | `redirectToMerchantWithHttpPost`                       | Hosted-page return                                            |
| `order_notification_enabled`                | `enableOrderNotification` + `webHookurl`               | Webhook delivery                                              |

## Common AI Mistakes

### Field naming and gotchas

- The `merchant-config.yml` keys are snake_case; the underlying MerchantAccount flag names are camelCase. The mapping is in the table above.
- A `false` value for a gate is **not** an error — it is a deliberate "this merchant has not opted into this feature." Suggest an alternative flow rather than asking for the gate to be enabled.

### Validation rules

- For loud gates, you can detect a missing gate at runtime via the `FEATURE_NOT_ENABLED` error response. For silent gates, you cannot — you must check `merchant-config.yml` ahead of time.
- The `payment_response_hash_enabled` gate requires both `enablePaymentResponseHash=true` AND `paymentResponseHashKey` set. If the key is missing, signing silently no-ops even if the flag is true.

### Doc-vs-code disagreements

- Public docs do not enumerate the silent-failure gates. They are derivable only from the source. Trust this card.

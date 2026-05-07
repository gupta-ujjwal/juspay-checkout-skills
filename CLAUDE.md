# CLAUDE.md — Working notes for `juspay-checkout-skills`

This file guides any AI agent (and the maintainer) working _on_ the skill bank. The skill cards themselves are merchant-facing; this file is for repo maintenance.

---

## Session resume — start here

**Where we are** (Phase 1 delivered):

- 7 base cards under `juspay-checkout-skill/_base/`: `auth_basic`, `auth_signature`, `environments`, `order_create`, `order_status`, `error_codes`, `merchant_gates`.
- 2 flow cards under `juspay-checkout-skill/flows/`: `cards_3ds`, `refund`.
- `juspay-checkout-skill/SKILL.md` is the index merchants land on.
- Structural rails: `dependencies.yml` (skill-ID registry), `merchant-config.yml.example` (per-merchant gate config template), `scripts/check.py` (validator that runs as the project's check + CI command).
- [`srid/agency`](https://github.com/srid/agency) installed via APM (`b3683da`) — see _Agency tooling_ below.

**What was decided** (don't re-litigate without reason):

- Source of truth is `~/juspay/euler-workspace-5/`, not the public docs (see _Source of truth_ below). Skill cards carry `verified_against:` frontmatter pointing at the snapshot used to author them, plus a `references:` list of public-doc URLs that merchants can resolve (since they don't have euler-workspace-5).
- Three integration modes: HyperCheckout, Express Checkout SDK, Express Checkout API. **Slicing is flow-primary** — one card per business flow, with conditional `### EC-API` / `### HyperCheckout` / `### EC-SDK` subsections inside the card for modes the flow supports. Platform variance lives in per-mode `integrations/` cards (Phase 3), not replicated per flow. See _Variant slicing_.
- Merchant-gate enforcement is structural: `merchant-config.yml` (fill-once) is consumed by the skill cards via `_base/merchant_gates.md`. Gated flows must list their gates in their _Merchant Enablement_ section; `scripts/check.py` validates the gate keywords appear in `merchant-config.yml.example`.
- Skill bank coexists with [`juspay-mcp`](https://github.com/juspay/juspay-mcp) — static-context vs dynamic-fetch.
- Scope is **global**, not SEA-specific (source docs are at `/sea/` but the bank is region-agnostic).

**What's next** — Phase 2: rest of the EC-API flows.

Add under `juspay-checkout-skill/flows/`: `cards_no_3ds`, `cards_3ds_frictionless`, `cards_preauth_capture`, `bank_transfers`, `wallets`, `rtp`, `mandates_registration`, `mandates_execution`, `customer_crud`, `payment_methods`, `void_capture`. Plus `_base/webhooks.md` (deferred from Phase 1 because no flow exercised it yet).

Each card additions to `dependencies.yml` in the same commit. Verify every endpoint, field, and error against `euler-workspace-5/`.

**Open decisions** (deferred, ask before acting):

- License file (Apache 2.0 placeholder in README — needs the actual `LICENSE` file).
- Distribution model (`curl | bash` vs `npm` vs `brew tap`).
- Per-region differences if they exist (currently using SEA docs as primary source).
- Phase 5 schema split: each card today serves three audiences (agent code-gen, maintainer verification, merchant config). Plan is to split to `flows/<x>.md` (agent-facing) + `.agency/<x>.verification.md` (maintainer code-traceback). Defer until after Phase 4.

---

## Source of truth

**Code beats docs, every time.** When the public docs at `juspay.io/sea/docs/` and the source at `~/juspay/euler-workspace-5/` disagree, code wins. The docs contradict themselves on Content-Type, omit auth schemes, and lag the implementation. Every claim in a skill card — endpoint path, field name, validation rule, error code, enablement gate — must be traceable to a file:line in `euler-workspace-5/`.

When skill cards reference a Juspay endpoint, use the **public path** (sandbox `https://sandbox.juspay.in`, prod `https://api.juspay.in`). Internal Servant routes carry an `/ecr` prefix that the edge proxy strips.

## Doc fetching recipe

The Juspay docs site exposes two helpers for LLMs:

1. **`.md` suffix on any doc URL** returns clean Markdown.

   ```bash
   curl -sSL https://juspay.io/sea/docs/ec-api-global/docs/order--payment-api-integration/create-order-apiorders.md
   ```

2. **Per-product `llms.txt`** lists every page with its `.md` link.
   ```bash
   curl -sSL https://juspay.io/sea/docs/hyper-checkout-sea/llms.txt
   curl -sSL https://juspay.io/sea/docs/express-checkout-sdk-global/llms.txt
   curl -sSL https://juspay.io/sea/docs/ec-api-global/llms.txt
   ```

Use these as starting points, then verify against code.

## Skill card schema

Each skill card lives in its own `.md` file with this frontmatter and section structure:

```markdown
---
name: skill-id-lowercase-hyphenated
description: One sentence — used by agents for relevance matching, so be specific
type: base | flow
applies_to: [hyper-checkout/android, ec-api, ...] # for non-base skills
metadata:
  author: Juspay
  version: "0.1.0"
  verified_against: euler-workspace-5@<short-sha>
---

## When to Apply

- Concrete user-intent triggers, e.g. "Implementing card 3DS payment via EC API"
- Lines starting with action verbs match better than vague descriptions

## Merchant Enablement

- (If the flow is gated) explicit list of merchant-account flags that must be enabled
- Rule: AI must ask the merchant to confirm before generating code

## Dependencies

- Named base skills, e.g. `auth_basic`, `environments`, `order_create`

## Execution Flow

1. Numbered steps, each ending in a concrete action
2. Cross-reference dependency outputs with `{{skill_id.output.field}}`

## Endpoints

| Environment | Method | URL |

## Request

- Headers
- Required fields with validation rules (max length, regex, allowed values)
- Optional fields
- Sample minimum payload
- Sample full payload (only if it adds value)

## Response

- Sample success
- State machine if applicable

## Error Handling

| HTTP | Error code | Cause | Action |

## Implementation Checklist for AI

- [ ] Step-by-step "do this, do not do that" list

## Common AI Mistakes

- Doc-vs-code gotchas this skill prevents
```

## Verified merchant-enablement gates

Use this list when writing the **Merchant Enablement** section of skill cards. Verified against `euler-workspace-5/euler-db/src/Euler/DB/Storage/Types/MerchantAccount.hs` and gate-check sites in `euler-api-txns/oltp/src-generated/Product/OLTP/`.

> **Subset surfaced via `merchant-config.yml.example`.** Most gates here are exposed in the per-merchant config file as boolean toggles. Four are intentionally omitted because they are not agent-configurable:
> `mandateConfig` (JSON blob), `basiliskKeyId` / `encryptionKeyIds` (JWE key material), `enabled` (master kill-switch), `enableSuccessRateBasedGatewayElimination` (internal tuning). Cards that need to reason about those flags must do so via maintainer guidance, not through `merchant-config.yml`.

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

## Merchant-facing endpoint inventory (verified)

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

## Variant slicing

The slicing is **flow-primary**: one card per business flow, with conditional integration subsections inside the card for the modes that flow supports. Platform variance (HyperCheckout SDK init, EC-SDK init, etc.) lives in per-mode `integrations/` cards (Phase 3) — _not_ replicated per flow.

```
juspay-checkout-skill/
├── SKILL.md                       # index merchants land on
├── _base/                         # shared, referenced by ID via `## Dependencies`
│   ├── auth_basic.md
│   ├── auth_signature.md
│   ├── auth_jwe.md                # Phase 3
│   ├── environments.md
│   ├── order_create.md
│   ├── order_status.md
│   ├── webhooks.md                # Phase 2
│   ├── error_codes.md
│   └── merchant_gates.md
├── flows/                         # one card per business flow; carries conditional
│                                  # ### EC-API / ### HyperCheckout / ### EC-SDK
│                                  # subsections for the modes the flow supports
│   ├── cards_3ds.md
│   ├── refund.md
│   └── …                          # Phase 2 adds the other ~12 EC-API flows
└── integrations/                  # Phase 3: one card per mode, with platform subsections
    ├── hyper-checkout.md          #   (Android / iOS / Web / React Native)
    ├── express-checkout-sdk.md    #   (Android / iOS / RN / Flutter / Cordova / Capacitor)
    └── express-checkout-api.md    #   REST conventions
```

Repo-root infrastructure that supports the bank:

```
dependencies.yml             # Registry of valid skill IDs. Every `## Dependencies`
                             # entry in any card must resolve here. scripts/check.py
                             # validates this; renames are caught immediately.
merchant-config.yml.example  # Per-merchant config template. Merchants copy to
                             # merchant-config.yml (gitignored) and fill in. Skills
                             # consult the file (via _base/merchant_gates.md) to
                             # avoid asking per-card whether each gate is enabled.
scripts/check.py             # Validator for frontmatter, dependency IDs, and gate
                             # keyword references. Stdlib-only Python.
```

## Multi-agent install matrix

| Agent              | Install location                                       | Format                                   | Notes                |
| ------------------ | ------------------------------------------------------ | ---------------------------------------- | -------------------- |
| GitHub Copilot CLI | `.github/skills/{name}/SKILL.md`                       | Frontmatter `name`, `description`        | Direct copy          |
| Claude Code        | `.claude/skills/{name}/` (proj) or `~/.claude/skills/` | Same shape as Copilot                    | Direct copy          |
| Cursor             | `.cursor/rules/*.mdc`                                  | MDC frontmatter (`globs`, `alwaysApply`) | Transform required   |
| Cline              | `.clinerules` (single file) or `.clinerules/*.md`      | Plain markdown                           | Concatenate or split |
| Codex CLI          | `AGENTS.md`                                            | Markdown                                 | Concatenate          |
| OpenCode           | `AGENTS.md` or `.opencode/`                            | Markdown                                 | Concatenate          |

`setup.sh` detects via presence of `.cursor/`, `.claude/`, `.clinerules`, etc.

## Phasing

1. **Phase 1 — delivered.** Smallest end-to-end useful slice: 7 base cards + 2 flow cards (`cards_3ds`, `refund`) so a merchant can "create order → 3DS pay → status → refund." Plus structural rails: `dependencies.yml`, `merchant-config.yml.example`, `scripts/check.py`.
2. **Phase 2** — Rest of EC-API flows (`cards_no_3ds`, `cards_3ds_frictionless`, `cards_preauth_capture`, `bank_transfers`, `wallets`, `rtp`, `mandates_registration`, `mandates_execution`, `customer_crud`, `payment_methods`, `void_capture`) plus `_base/webhooks.md`.
3. **Phase 3** — `integrations/{hyper-checkout,express-checkout-sdk,express-checkout-api}.md` with platform subsections inside; `_base/auth_jwe.md`. This is where the per-platform SDK init / lifecycle code lives. **Extraction step:** when the HyperCheckout and EC-SDK subsections in flow cards (currently stubbed under each `### HyperCheckout integration` / `### Express Checkout SDK integration` heading) get fully populated, the mode-specific *payload* shapes move out to the corresponding `integrations/` card. The flow card's body keeps the universal sequence (create order → initiate → handle challenge → poll status); each per-mode subsection becomes a one-line cross-reference into the integration card. This avoids forcing reviewers to hold three payload grammars in their head while reading a single flow.
4. **Phase 4** — `setup.sh` multi-agent installer + format transforms (Cursor `.mdc`, Cline, Codex, OpenCode).
5. **Phase 5** — Schema split (per-card `.verification.md` companion files) + license + cross-skill consistency review + public release.

## Open items

- License file (Apache 2.0 implied — need to add).
- Distribution model (`curl | bash` vs `npm` vs `brew tap`) — deferred.
- Per-region differences (SEA vs IN vs Global) — currently using SEA docs as source; if features differ across regions, surface in skill metadata.

---

## Agency tooling

This repo uses [`srid/agency`](https://github.com/srid/agency) installed via [APM](https://github.com/srid/apm). The framework's files live alongside the skill bank — they're for _building_ the bank, not part of what merchants consume.

- `apm.yml` — declares `srid/agency#master` as a dependency. Run `apm install` to refresh.
- `apm_modules/srid/agency/` — installed framework (gitignored).
- `.agency/do.md` — config for the `/do` slash command (check/format/test/CI commands). Check and CI both run `python3 scripts/check.py`; format runs `prettier --write '**/*.md'`. Update when commands change.
- `.claude/skills/` — agency skills available in this repo: `code-police`, `do`, `elegance`, `fact-check`, `forge-pr`, `hickey`, `lowy`, `ralph`, `talk`.
- `.claude/agents/` — `hickey.md`, `lowy.md` subagents.
- `.claude/rules/` — `apm-sources.md`, `conventions.md` — read these at the start of any session.
- `.claude/settings.json` — `Stop` hook runs `.claude/hooks/agency/scripts/do-stop-guard.sh` (the `/do` enforcement).

When iterating on the skill bank, prefer the agency skills where they fit — `/do` for check/format/CI, `forge-pr` for PRs, `fact-check` for verification claims.

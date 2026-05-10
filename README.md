# Juspay Checkout Skills

Agent Skills for integrating with Juspay's checkout products. Drop these into your coding agent (Copilot, Cursor, Claude Code, Cline, Codex, OpenCode) and it gets grounded, code-verified context for **HyperCheckout**, **Express Checkout SDK**, and **Express Checkout API** — instead of guessing endpoint shapes from training data.

> **Status:** under construction. Not yet ready for merchant use.

## Status

Phase 1 is sub-phased and ships **HyperCheckout end-to-end** as one complete vertical. Express Checkout SDK is Phase 2; Express Checkout Backend is Phase 3.

| Sub-phase                                  | Cards                                                                     | State       |
| ------------------------------------------ | ------------------------------------------------------------------------- | ----------- |
| 1A — spine                                 | bank `SKILL.md`, `foundations/{authentication, webhooks-and-signatures}/` | shipped     |
| 1B-HC — api-references HyperCheckout calls | `api-references/{session, order-status, refund-order}/`                   | next        |
| 1C-HC — orchestrator                       | `integrations/hyper-checkout/`                                            | after 1B-HC |

---

## What this is

A repository of structured Markdown skill cards organised as a five-layer bank: foundations (cross-cutting concerns), API references (one skill per Juspay API), integration orchestrators (HyperCheckout / Express Checkout SDK / Express Checkout Backend), a go-live checklist, and a bank-level entry point. Each skill carries a crisp activation trigger, a single responsibility, and links to the other skills it depends on.

Inspired by [PhonePe's `phonepe-pg-skills`](https://github.com/PhonePe/phonepe-pg-skills). The full framework — layers, `SKILL.md` anatomy, naming, splitting heuristics, authoring quality bar, phasing — lives in [`docs/framework.md`](./docs/framework.md).

## Structure

| Layer                 | What it owns                                                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`foundations/`**    | Cross-cutting concerns: authentication, webhooks-and-signatures, and (later) idempotency-and-retries, error model, sandbox-and-testing                                          |
| **`api-references/`** | One skill per Juspay API. Full superset schema; payment-flow variants (mandates, pre-auth, decoupled) folded in as variant sections later                                       |
| **`integrations/`**   | Per-product orchestrators. Phase 1 ships `hyper-checkout`; Phase 2 adds `express-checkout-sdk`; Phase 3 adds `express-checkout-backend`. Delegate payloads to `api-references/` |
| **`go-live/`**        | Production-readiness checklist (later phase)                                                                                                                                    |
| **Bank `SKILL.md`**   | Top-level entry point that orients the agent across the bank                                                                                                                    |

## Skill bank vs. MCP server

Juspay also publishes [`juspay-mcp`](https://github.com/juspay/juspay-mcp) — a Model Context Protocol server that lets agents fetch docs at runtime. The two tools are complementary:

|             | Skill bank (this repo)                | `juspay-mcp`                  |
| ----------- | ------------------------------------- | ----------------------------- |
| When loaded | At agent startup, into context        | On-demand, per tool call      |
| Latency     | None at use time                      | Network round-trip per fetch  |
| Coverage    | Curated, code-verified flows          | All published docs            |
| Best for    | Common integrations, offline work, CI | Deep dives, less-common flows |

Use both together if you want.

## Installation

A `setup.sh` will detect your coding agent and install the skills into the right path:

| Agent                             | Install location                                          |
| --------------------------------- | --------------------------------------------------------- |
| GitHub Copilot CLI / coding agent | `.github/skills/`                                         |
| Claude Code                       | `.claude/skills/` (project) or `~/.claude/skills/` (user) |
| Cursor                            | `.cursor/rules/` (transformed to `.mdc`)                  |
| Cline                             | `.clinerules`                                             |
| Codex CLI / OpenCode              | `AGENTS.md`                                               |

```bash
# Coming soon
curl -fsSL https://raw.githubusercontent.com/juspay/juspay-checkout-skills/main/setup.sh | bash
```

## Source

Skill cards are grounded in the Juspay Euler source code — not just the public docs — to avoid AI agents copying outdated or contradictory documentation.

## Scope

This bank teaches a coding agent how to integrate Juspay on the **merchant's backend**. In scope: server-to-server API calls (create order, create session, create customer, txns, refunds), webhook receivers, order-status reconciliation, and the response payload the backend hands to its frontend so the SDK can initialise. Out of scope: SDK rendering, iframe handling, payment-URL loading, per-platform initialisation code. Those are frontend concerns and may be covered by a separate bank later.

## Phase 1 omissions

Some Juspay capabilities are gated by `MerchantAccount` flags that fail **silently** — the call appears to succeed, the integration looks healthy, the feature quietly does nothing. To avoid implying these capabilities are unconditionally available, Phase 1 cards exclude flows or steps that depend on a silent gate. The exclusions below will be addressed in Phase 2 once we decide where merchant-enablement gates land in the bank (foundation skill vs inline citations vs hybrid).

| Excluded from Phase 1                                                                | Gate (in `MerchantAccount`)                                                         | Why excluded                                                    |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| HMAC signature verification on webhooks and return URLs                              | `enablePaymentResponseHash` + `paymentResponseHashKey`                              | Off → callbacks unsigned, no error                              |
| Save-card-before-auth (tokenisation before authorisation)                            | `enableSaveCardBeforeAuth`                                                          | Off → flow omitted from response                                |
| OTP-based payment authentication                                                     | `otpEnabled`                                                                        | Off → step omitted, no error                                    |
| Reverse token                                                                        | `reverseTokenEnabled`                                                               | Off → flow omitted                                              |
| Mandate flows (registration, execution, auto-retry, auto-revoke, per-gateway config) | `mandateAutoRevokeEnabled`, `executeMandateAutoRetryEnabled`, `mandateConfig`, etc. | Multiple silent gates; full mandate variant deferred to Phase 2 |
| EMI / installments                                                                   | `installmentEnabled`                                                                | Off → flow omitted                                              |
| Offers engine                                                                        | `offerEnabled`                                                                      | Off → no offers attached, no error                              |
| Automatic retry                                                                      | `enableAutomaticRetry`                                                              | Off → no retry, no error                                        |
| Success-rate-based gateway elimination                                               | `enableSuccessRateBasedGatewayElimination`                                          | Off → routing not applied                                       |
| Gateway health-based routing                                                         | `gatewayDecidedByHealthEnabled`                                                     | Off → routing not applied                                       |
| External risk check                                                                  | `enableExternalRiskCheck`                                                           | Off → step skipped                                              |
| Auto-refund on conflicts / duplicate charges                                         | `autoRefundConflictTransactions`, `autoRefundMultipleChargedTransactions`           | Off → no auto-refund, no error                                  |
| HTTP POST redirect on `return_url`                                                   | `redirectToMerchantWithHttpPost`                                                    | Off → GET redirect instead                                      |
| Order/conflict notification webhook delivery                                         | `enableOrderNotification`, `enableConflictStatusNotification` + `webHookurl`        | Off → no notification                                           |
| JWE auth on `/v4/*` endpoints                                                        | `basiliskKeyId` + `encryptionKeyIds`                                                | Off → encrypted endpoints unusable                              |

The full gate inventory (including loud-failing gates that are documented inline rather than excluded) is in [`.claude/rules/reference-data.md`](./.claude/rules/reference-data.md).

## Contributing

Skill cards must be code-verified. The structural framework (layers, `SKILL.md` anatomy, naming, quality bar) lives in [`docs/framework.md`](./docs/framework.md); the maintainer rules (source-of-truth discipline, doc-fetch recipe, Phase 1 scope) live in [`.claude/rules/conventions.md`](./.claude/rules/conventions.md); the verified-against-source data (merchant-enablement gates, endpoint inventory) lives in [`.claude/rules/reference-data.md`](./.claude/rules/reference-data.md). [`CLAUDE.md`](./CLAUDE.md) is the session-resume entry point.

## License

Apache License 2.0 — to be added before public release.

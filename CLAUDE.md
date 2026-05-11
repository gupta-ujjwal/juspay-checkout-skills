# CLAUDE.md — Working notes for `juspay-checkout-skills`

This file guides any AI agent (and the maintainer) working _on_ the skill bank. The skill cards themselves are merchant-facing; this file is for repo maintenance.

---

## Session resume — start here

**Where we are** — Phase 1 narrowed to **HyperCheckout end-to-end**. Express Checkout SDK and Express Checkout Backend become Phase 2 and Phase 3 respectively.

- **1A (spine) — shipped** in PR #7 (commit `43323e1` on main): `skills/SKILL.md`, `skills/foundations/authentication/SKILL.md`, `skills/foundations/webhooks-and-signatures/SKILL.md`.
- **PR-A scope-narrow + ref-data corrections — shipped** in PR #10 (commit `e5d68df` on main): closed #3.
- **1B-HC (api-references HyperCheckout calls) — shipped** in PR #12: `api-references/{session, order-status, refund-order}/`. Each declares its own auth scheme and required headers; foundation auth card shrunk to scheme-proper (closes #6 and #9). Reference-data correction landed inline: `enabledInstantRefund` raises **400** (not 403) from `Refund/Validation.hs:1072` (not `Decider.hs`). Round-1 user feedback (no internal code refs in cards, version-header mandatory for new merchants, base URLs consolidated, session required-fields restructured, `epg_txn_id` surfaced, `TO_BE_CHARGED` semantic corrected, dual native/web handoff documented) landed inside the same PR before merge.
- **1C-HC (orchestrator) — shipped** in this PR: `integrations/hyper-checkout/`. The "reconcile via order-status" pattern relocated from `foundations/webhooks-and-signatures/` (closes #5); auth foundation's per-route header card-list collapsed to a generic pointer (closes #11). **Phase 1 is complete.**

**Bank scope is backend-only** — server-to-server APIs and the response payload that the merchant's backend hands to its frontend SDK. SDK rendering, iframe handling, and per-platform initialisation are out of scope (future separate bank).

**Where to read what**:

- [`docs/framework.md`](./docs/framework.md) — the structural framework: five layers, `SKILL.md` anatomy, naming, splitting heuristics, authoring quality bar, phasing.
- [`.claude/rules/conventions.md`](./.claude/rules/conventions.md) — maintenance rules: source-of-truth discipline, doc-fetching, Phase 1 scope, silent-gate exclusion, orchestrator–api-reference contract, multi-agent install matrix.
- [`.claude/rules/reference-data.md`](./.claude/rules/reference-data.md) — verified-against-`euler-workspace-5/` data: merchant-enablement gates table, merchant-facing endpoint inventory, auth schemes.
- [`README.md`](./README.md) §"Phase 1 omissions" — the merchant-facing list of silent-gated capabilities deferred to Phase 2.

**Verification rule.** Every claim in a card must cite a `euler-workspace-5/` `file:line`. Code beats docs when the two disagree.

**Open decisions** (deferred, ask before acting):

- License file (Apache 2.0 placeholder in README — needs the actual `LICENSE` file).
- Distribution model (`curl | bash` vs `npm` vs `brew tap`).
- Per-region differences if they exist (currently using SEA docs as primary source).
- **Phase 2:** where merchant-enablement gates land (a `foundations/merchant-enablement/` skill, inline citations inside affected api-reference variants, or both). Don't pre-decide while authoring Phase 1 cards.

**Reference-data corrections (closed by PR-A — issue #3):**

The original #3 framed two stale rows. Re-verifying against `euler-workspace-5/` revealed the picture was different:

- KeyAuth row was **operationally right** in saying "Authorization plus `x-merchantid`". The auth scheme proper (`AuthKeyService.hs:46-71`) reads only `Authorization`, but most KeyAuth-protected routes additionally require `x-merchantid` (route handlers construct `XMerchantId` for downstream context, e.g. `Server.hs:6714`) and `x-routing-id` (enforced by `withXRoutingId` middleware at `Server.hs:339`). Both IN and SEA public docs uniformly require all three. The Phase 1A foundation auth card had over-corrected by stating `x-merchantid` is "not part of KeyAuth" — that has been reverted in PR-A and now reflects the route-level header reality.
- Webhook HMAC row **was** wrong. `paymentResponseHashKey` is verified only in return-URL signing (`PaymentStatusHelpers.hs:54`); outbound webhook delivery uses HTTP Basic Auth (merchant-configured creds, not gated, not HMAC). The row is renamed to "Return-URL HMAC signing" and a clarifying note distinguishes the two mechanisms.
- Endpoint inventory listed `GET|POST /order/status` — wrong path. The canonical merchant-facing route is `GET /orders/{order_id}` (`Server.hs:2540`, `OrderStatusUrlCapture`); `/order/payment-status` (`Server.hs:2461`) is a distinct txn-level route; `/orderStatus?order_id=` is a legacy query-param variant. The webhooks foundation card pointed at `/order/status` — fixed in PR-A to `GET /orders/{order_id}`.

---

## Agency tooling

This repo uses [`srid/agency`](https://github.com/srid/agency) installed via [APM](https://github.com/srid/apm). The framework's files live alongside the skill bank — they're for _building_ the bank, not part of what merchants consume.

- `apm.yml` — declares `srid/agency#master` as a dependency. Run `apm install` to refresh.
- `apm_modules/srid/agency/` — installed framework (gitignored).
- `.agency/do.md` — config for the `/do` slash command (check/format/test/CI commands). Currently `markdownlint **/*.md` for check, `prettier --write **/*.md` for format. Update when we have real CI.
- `.claude/skills/` — agency skills available in this repo: `code-police`, `do`, `elegance`, `fact-check`, `forge-pr`, `hickey`, `lowy`, `ralph`, `talk`.
- `.claude/agents/` — `hickey.md`, `lowy.md` subagents.
- `.claude/rules/` — `apm-sources.md`, `conventions.md`. **`conventions.md` is generated** from `.apm/instructions/conventions.instructions.md` by `apm install`; edit the source, not the generated file.
- `.claude/settings.json` — `Stop` hook runs `.claude/hooks/agency/scripts/do-stop-guard.sh` (the `/do` enforcement).

When iterating on the skill bank, prefer the agency skills where they fit — `/do` for check/format/CI, `forge-pr` for PRs, `fact-check` for verification claims.

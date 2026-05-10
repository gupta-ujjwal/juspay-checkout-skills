# CLAUDE.md — Working notes for `juspay-checkout-skills`

This file guides any AI agent (and the maintainer) working _on_ the skill bank. The skill cards themselves are merchant-facing; this file is for repo maintenance.

---

## Session resume — start here

**Where we are** — Phase 1 sub-phased into 1A → 1B → 1C; each sub-phase ships independently:

- **1A (the spine) — in flight on `skills/phase-1a-spine`**: `skills/SKILL.md`, `skills/foundations/authentication/SKILL.md`, `skills/foundations/webhooks-and-signatures/SKILL.md`. Plus convention additions (orchestrator-link rule, silent-gate exclusion) and a README §"Phase 1 omissions" section enumerating the silent-gated capabilities Phase 1 cards deliberately don't cover.
- **1B (api-references) — not started**: `order-create/`, `session/`, `txns/`, `create-customer/` (and `order-status/` if needed for the orchestrators).
- **1C (orchestrators) — not started**: `hyper-checkout/`, `express-checkout-sdk/`, `express-checkout-backend/`. Each is a single platform-agnostic backend sequence card; orchestrators link to api-references for payloads, never inline schemas.

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

**Reference-data corrections discovered during 1A authoring** — tracked as [#3](https://github.com/gupta-ujjwal/juspay-checkout-skills/issues/3) (KeyAuth `x-merchantid` row + webhook HMAC field attribution). Out of scope for 1A; the issue describes both corrections with `euler-workspace-5/` citations.

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

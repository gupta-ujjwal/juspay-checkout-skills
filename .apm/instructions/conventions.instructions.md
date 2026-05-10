---
description: Working notes for maintainers and AI agents authoring the juspay-checkout-skills skill bank. The structural framework lives in docs/framework.md; verified-against-source data (gates table, endpoint inventory) lives in reference-data.md. This file covers source-of-truth discipline, doc-fetching shortcuts, the Phase 1 scope, and the multi-agent install matrix.
---

This file guides any AI agent (and the maintainer) working _on_ the skill bank. The skill cards themselves are merchant-facing; this file is for repo maintenance.

The structural framework — five layers, `SKILL.md` anatomy, naming, splitting heuristics, authoring quality bar, phasing — is defined in [`docs/framework.md`](../../docs/framework.md). Read it before authoring any skill. The verified-against-source data (merchant-enablement gates, endpoint inventory) lives in [`reference-data.md`](./reference-data.md) — separate file because it tracks `euler-workspace-5/` advances on its own cadence. This file holds working rules: source-of-truth discipline, doc-fetching, the Phase 1 scope, and the multi-agent install matrix.

**Bank root in this repo:** `skills/`.

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

## Phase 1 scope

Per `docs/framework.md` §7, Phase 1 ships the spine:

- `skills/SKILL.md` — bank-level entry point.
- `skills/foundations/authentication/` and `skills/foundations/webhooks-and-signatures/`.
- `skills/integrations/{hyper-checkout, express-checkout-sdk, express-checkout-backend}/` — happy-path orchestration only.
- `skills/api-references/` for the critical-path APIs the integrations call: Order Create, Session, Txns, Create Customer.

**Deferred to Phase 2:** flow-variant sections inside api-references (mandates, decoupled, pre-auth) and merchant-enablement gate placement (foundation skill vs inline citations vs hybrid). Don't pre-decide these in Phase 1 cards — leave gate-affected variants out and let Phase 2 work resolve where they live.

**Phase 1 silent-gate exclusion.** Some merchant-enablement gates fail silently — the call appears to succeed, the capability quietly does nothing. Phase 1 cards omit any step or mechanism that depends on a silent gate; the deferred list is enumerated in [`README.md`](../../README.md) §"Phase 1 omissions". When authoring a card, cross-check `reference-data.md` for "Silent" rows that touch your scope and either exclude the affected step or move it to a "deferred to Phase 2" section with a pointer to the omissions list.

**Bank scope: backend-only.** Cards target the merchant's backend agent. In scope: server-to-server API calls, webhook receivers, and the response payload the backend hands to the frontend so the SDK can initialise. Out of scope: SDK rendering, iframe handling, payment-URL loading, per-platform initialisation. If a card needs frontend SDK code, that's the wrong card — it belongs in a future frontend bank.

## Orchestrator–api-reference contract

Orchestrators describe sequence; api-references describe payloads. The contract:

- Orchestrators **link** to api-reference cards for payload details — they never inline schemas, field lists, or error tables.
- When Phase 2 adds flow variants (mandates, decoupled, pre-auth) inside api-references, orchestrators **link to the variant section** rather than branching internally on the flow. An orchestrator stays linear; conditionality lives one layer down. (Per Lowy: variants are an axis of change inside api-references; if an orchestrator branches on flow, the flow-axis volatility leaks into the integration layer.)
- If you find yourself writing field names inside an orchestrator, stop — that content belongs in the api-reference and the orchestrator should link.

### Worked counter-example — do not do this

A Phase 2 author touching `integrations/express-checkout-sdk/SKILL.md` to add mandate support might be tempted to write:

```markdown
## Step 2 — create the order

### For one-time payments

POST `/orders` with `order_id`, `amount`, `currency`, `customer_id`...

### For mandates

POST `/orders` with `order_id`, `amount`, `currency`, `customer_id`,
`mandate.max_amount`, `mandate.frequency`, `mandate.start_date`...

### For pre-auth

POST `/orders` with `order_id`, `amount`, `currency`, `auto_capture: false`...
```

This violates the contract three ways: payload field names are inlined (orchestrator complecting api-reference content), the orchestrator branches on flow (flow-axis volatility leaking up from `api-references/order-create/`), and per-flow sections will diverge from the api-reference's own variant sections as both evolve.

Instead, write a single linear step that links into the api-reference's variant section:

```markdown
## Step 2 — create the order

Call `POST /orders` per `api-references/order-create/`. Pick the variant:

- One-time payments: §"Happy path" of `api-references/order-create/SKILL.md`.
- Mandate flows: §"Mandate variant" of `api-references/order-create/SKILL.md`.
- Pre-auth flows: §"Pre-auth variant" of `api-references/order-create/SKILL.md`.
```

The orchestrator stays linear; conditionality is delegated to the api-reference.

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

## Open items

- License file (Apache 2.0 implied — need to add).
- Distribution model (`curl | bash` vs `npm` vs `brew tap`) — deferred.
- Per-region differences (SEA vs IN vs Global) — currently using SEA docs as source; if features differ across regions, surface in skill metadata.

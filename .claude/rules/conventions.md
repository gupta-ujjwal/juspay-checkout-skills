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

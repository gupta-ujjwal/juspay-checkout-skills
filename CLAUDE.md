# CLAUDE.md — Working notes for `juspay-checkout-skills`

This file guides any AI agent (and the maintainer) working _on_ the skill bank. The skill cards themselves are merchant-facing; this file is for repo maintenance.

---

## Session resume — start here

**Where we are** (as of commit `b3683da`):

- Repo initialised on `main`, pushed to `github.com/gupta-ujjwal/juspay-checkout-skills`.
- README, this CLAUDE.md, and `.gitignore` committed in `24bb37b`.
- [`srid/agency`](https://github.com/srid/agency) installed via APM in `b3683da` — see _Agency tooling_ below.
- Skill bank framework adopted from [`docs/framework.md`](./docs/framework.md). `PHASE1-LEARNINGS.md` is superseded — kept as historical context.
- **No skill cards written yet.** `skills/` directory does not exist yet.

**Where to read what**:

- [`docs/framework.md`](./docs/framework.md) — the structural framework: five layers, `SKILL.md` anatomy, naming, splitting heuristics, authoring quality bar, phasing.
- [`.claude/rules/conventions.md`](./.claude/rules/conventions.md) — maintenance rules: source-of-truth discipline, doc-fetching, Phase 1 scope, multi-agent install matrix.
- [`.claude/rules/reference-data.md`](./.claude/rules/reference-data.md) — verified-against-`euler-workspace-5/` data: merchant-enablement gates table, merchant-facing endpoint inventory, auth schemes. Updates on its own cadence when source advances.

**What's next** — Phase 1, the spine. The deliverable list lives in [`.claude/rules/conventions.md`](./.claude/rules/conventions.md) §Phase 1 scope; that file is the single source so this section can't drift.

Verify every endpoint, field, and error against `euler-workspace-5/`. The endpoint inventory in `.claude/rules/reference-data.md` is the starting map. Use the doc-fetch recipe (in conventions) for prose context, then ground in code.

**Open decisions** (deferred, ask before acting):

- License file (Apache 2.0 placeholder in README — needs the actual `LICENSE` file).
- Distribution model (`curl | bash` vs `npm` vs `brew tap`).
- Per-region differences if they exist (currently using SEA docs as primary source).
- **Phase 2:** where merchant-enablement gates land (a `foundations/merchant-enablement/` skill, inline citations inside affected api-reference variants, or both). Don't pre-decide while authoring Phase 1 cards.

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

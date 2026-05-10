# Juspay Checkout Skills

Agent Skills for integrating with Juspay's checkout products. Drop these into your coding agent (Copilot, Cursor, Claude Code, Cline, Codex, OpenCode) and it gets grounded, code-verified context for **HyperCheckout**, **Express Checkout SDK**, and **Express Checkout API** — instead of guessing endpoint shapes from training data.

> **Status:** under construction. Not yet ready for merchant use.

---

## What this is

A repository of structured Markdown skill cards organised as a five-layer bank: foundations (cross-cutting concerns), API references (one skill per Juspay API), integration orchestrators (HyperCheckout / Express Checkout SDK / Express Checkout Backend), a go-live checklist, and a bank-level entry point. Each skill carries a crisp activation trigger, a single responsibility, and links to the other skills it depends on.

Inspired by [PhonePe's `phonepe-pg-skills`](https://github.com/PhonePe/phonepe-pg-skills). The full framework — layers, `SKILL.md` anatomy, naming, splitting heuristics, authoring quality bar, phasing — lives in [`docs/framework.md`](./docs/framework.md).

## Structure

| Layer                 | What it owns                                                                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`foundations/`**    | Cross-cutting concerns: authentication, idempotency-and-retries, webhooks-and-signatures, error model, sandbox-and-testing                                                            |
| **`api-references/`** | One skill per Juspay API (Order Create, Session, Txns, Create Customer, …). Full superset schema; payment-flow variants (mandates, pre-auth, decoupled) folded in as variant sections |
| **`integrations/`**   | Three orchestrators: `hyper-checkout`, `express-checkout-sdk`, `express-checkout-backend`. Own the sequence of API calls; delegate payloads to `api-references/`                      |
| **`go-live/`**        | Production-readiness checklist                                                                                                                                                        |
| **Bank `SKILL.md`**   | Top-level entry point that orients the agent across the bank                                                                                                                          |

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

## Contributing

Skill cards must be code-verified. The structural framework (layers, `SKILL.md` anatomy, naming, quality bar) lives in [`docs/framework.md`](./docs/framework.md); the maintainer rules (source-of-truth discipline, doc-fetch recipe, Phase 1 scope) live in [`.claude/rules/conventions.md`](./.claude/rules/conventions.md); the verified-against-source data (merchant-enablement gates, endpoint inventory) lives in [`.claude/rules/reference-data.md`](./.claude/rules/reference-data.md). [`CLAUDE.md`](./CLAUDE.md) is the session-resume entry point.

## License

Apache License 2.0 — to be added before public release.

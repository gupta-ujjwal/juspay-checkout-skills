# Juspay Checkout Skills

Agent Skills for integrating with Juspay's checkout products. Drop these into your coding agent (Copilot, Cursor, Claude Code, Cline, Codex, OpenCode) and it gets grounded, code-verified context for **HyperCheckout**, **Express Checkout SDK**, and **Express Checkout API** — instead of guessing endpoint shapes from training data.

> **Status:** under construction. Not yet ready for merchant use.

---

## What this is

A repository of structured Markdown skill cards. Each card documents one Juspay flow — order create, card 3DS transaction, mandate registration, refund, etc. — with the exact endpoint, required and optional fields with validation rules, error codes with recommended actions, and an implementation checklist for AI agents.

Inspired by [PhonePe's `phonepe-pg-skills`](https://github.com/PhonePe/phonepe-pg-skills).

## Coverage

| Integration mode | Platforms | Description |
|---|---|---|
| **HyperCheckout** | Android, iOS, Web, React Native | Pre-built, customisable hosted checkout UI |
| **Express Checkout SDK** | Android, iOS, React Native, Flutter, Cordova, Capacitor | Build your own UI on top of Juspay's SDK |
| **Express Checkout API** | REST | Server-to-server APIs, no SDK |

Plus shared base skills (auth, environments, order create, order status, refund, webhooks, error codes, HMAC verification) referenced from all three modes.

## Skill bank vs. MCP server

Juspay also publishes [`juspay-mcp`](https://github.com/juspay/juspay-mcp) — a Model Context Protocol server that lets agents fetch docs at runtime. The two tools are complementary:

| | Skill bank (this repo) | `juspay-mcp` |
|---|---|---|
| When loaded | At agent startup, into context | On-demand, per tool call |
| Latency | None at use time | Network round-trip per fetch |
| Coverage | Curated, code-verified flows | All published docs |
| Best for | Common integrations, offline work, CI | Deep dives, less-common flows |

Use both together if you want.

## Installation

A `setup.sh` will detect your coding agent and install the skills into the right path:

| Agent | Install location |
|---|---|
| GitHub Copilot CLI / coding agent | `.github/skills/` |
| Claude Code | `.claude/skills/` (project) or `~/.claude/skills/` (user) |
| Cursor | `.cursor/rules/` (transformed to `.mdc`) |
| Cline | `.clinerules` |
| Codex CLI / OpenCode | `AGENTS.md` |

```bash
# Coming soon
curl -fsSL https://raw.githubusercontent.com/juspay/juspay-checkout-skills/main/setup.sh | bash
```

## Source

Skill cards are grounded in the Juspay Euler source code — not just the public docs — to avoid AI agents copying outdated or contradictory documentation.

## Contributing

Skill cards must be code-verified. See [CLAUDE.md](./CLAUDE.md) for the schema and verification workflow.

## License

Apache License 2.0 — to be added before public release.

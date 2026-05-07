# Juspay Checkout Skills

Agent Skills for integrating with Juspay's checkout products. Drop these into your coding agent (Copilot, Cursor, Claude Code, Cline, Codex, OpenCode) and it gets grounded, code-verified context for **HyperCheckout**, **Express Checkout SDK**, and **Express Checkout API** — instead of guessing endpoint shapes from training data.

> **Status:** Phase 1 delivered (EC-API path: create order → 3DS card payment → status → refund). HyperCheckout and Express Checkout SDK adapters land in Phase 3. Not yet ready for production merchant use — schema and structure may still change.

---

## What this is

A repository of structured Markdown skill cards. Each card documents one Juspay flow — order create, card 3DS transaction, mandate registration, refund, etc. — with the exact endpoint, required and optional fields with validation rules, error codes with recommended actions, and an implementation checklist for AI agents.

Inspired by [PhonePe's `phonepe-pg-skills`](https://github.com/PhonePe/phonepe-pg-skills).

## Coverage

| Integration mode         | Platforms                                               | Description                                |
| ------------------------ | ------------------------------------------------------- | ------------------------------------------ |
| **HyperCheckout**        | Android, iOS, Web, React Native                         | Pre-built, customisable hosted checkout UI |
| **Express Checkout SDK** | Android, iOS, React Native, Flutter, Cordova, Capacitor | Build your own UI on top of Juspay's SDK   |
| **Express Checkout API** | REST                                                    | Server-to-server APIs, no SDK              |

Plus shared base skills (auth, environments, order create, order status, error codes, merchant gates, refund, webhooks, HMAC verification) referenced from all three modes.

The slicing is **flow-primary**: each business flow (e.g. card 3DS payment) is one card with conditional `### EC-API` / `### HyperCheckout` / `### EC-SDK` subsections inside. Per-mode SDK init and platform-specific concerns live in separate `integrations/` cards (Phase 3).

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

## Per-merchant configuration

Once installed, copy `merchant-config.yml.example` to `merchant-config.yml` (gitignored) and fill in the values for your merchant account — which API auth scheme, which gates are enabled in your Juspay merchant dashboard, your webhook URL, etc. AI agents read this file via `_base/merchant_gates.md` to skip per-card enablement prompts.

Gates with the value `unknown` (the default) cause the agent to ask before generating code that depends on them. Set them to `true` or `false` once you've confirmed in the Juspay merchant dashboard.

## Source

Skill cards are grounded in the Juspay Euler source code — not just the public docs — to avoid AI agents copying outdated or contradictory documentation. Each card carries a `references:` block of public-doc URLs (which you can resolve) and a `verified_against:` snapshot marker for maintainers (referencing internal Juspay source you don't need access to).

## Contributing

Skill cards must be code-verified. See [CLAUDE.md](./CLAUDE.md) for the schema and verification workflow.

## License

Apache License 2.0 — to be added before public release.

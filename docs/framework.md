# Juspay Skill Bank — Framework and Structure

_A research-backed framework for building an agent-readable skill bank for Juspay's payment APIs and integration types._

---

## 1. Problem Statement

Modern coding is increasingly performed by AI agents (Claude Code, Copilot, Cursor, Codex, etc.) rather than humans. For Juspay, this means the primary "developer" integrating with Express Checkout and other Juspay products is now often an agent acting on behalf of a merchant.

Today, agents integrating with payment APIs face several recurring problems:

- **API documentation is human-shaped, not agent-shaped.** It's discoverable through search and navigation, not through structured activation triggers an agent can match against a user's intent.
- **Payment integration has many legitimate axes of variation** — different integration types (backend-only, SDK-hybrid, hosted), different payment instruments and flows (cards, UPI Intent vs Collect, mandates, pre-auth, decoupled), different lifecycle operations (initiate, capture, refund, query) — and naive documentation collapses these into prose that the agent has to re-derive every time.
- **Cross-cutting concerns get duplicated or lost.** Authentication, idempotency, webhook handling, and error semantics apply to every flow, but if they live inside individual integration guides, every guide drifts and updates become painful.
- **Agents need to compose, not just look up.** A merchant building "subscriptions with card mandate on the SDK" needs the agent to assemble multiple primitives in the right sequence — not read a single megapage.

A **skill bank** solves this by packaging Juspay's integration knowledge as a structured set of agent-readable skills, where each skill has a crisp activation trigger, a single responsibility, and clear links to the other skills it depends on.

---

## 2. Solution Overview

The skill bank is organized around a simple insight from researching Stripe, PayPal, PhonePe, and the Agent Skills Specification:

> **APIs and payment flows are stable building blocks. Integration types are orchestrators that compose them.**

This separation drives the entire structure. We build atomic API reference skills once, and the three integration types (HyperCheckout, ExpressCheckout-SDK, ExpressCheckout-Backend) reference them as needed, owning only the _sequence_ and _decisions_ specific to their shape.

The bank has five layers:

1. **Foundations** — cross-cutting concerns (auth, idempotency, webhooks, error model, sandbox) that every integration depends on. Authored once, referenced everywhere.
2. **API References** — one skill per Juspay API, documenting the _full superset_ schema with payment-flow variants folded in as conditional sections. This is the single source of truth for any API call.
3. **Integrations** — orchestrator skills for HyperCheckout, ExpressCheckout-SDK, and ExpressCheckout-Backend. They own the sequence of API calls and integration-specific gotchas, and delegate payload details to API References.
4. **Go-Live** — production-readiness checklist that helps merchants validate their integration before turning on real traffic.
5. **Bank-level entry point** — a top-level `SKILL.md` that tells the agent how to navigate the bank.

The framework is grounded in four principles (single responsibility, discoverable activation, progressive disclosure, composability) and uses progressive disclosure to keep agent context windows lean: metadata always loaded, instructions on activation, references on demand.

---

## 3. Framework Foundations

### 3.1 The Four Core Principles

Every skill in the bank must satisfy these. They're derived from the consensus across Stripe, PayPal, PhonePe, and the Agent Skills Specification.

**Single Responsibility.** A skill answers exactly one question or performs exactly one job. If a skill's description contains "and" between two distinct verbs, it should likely be split.

**Discoverable Activation.** Every skill has a crisp `Use when…` clause in its description. Agents don't run classifiers — they read descriptions and decide. The trigger language must include the user-facing intent, concrete keywords likely to appear in agent prompts, and disambiguating context that prevents wrong-skill activation.

**Progressive Disclosure.** Three context tiers, all in the same skill:

- _Tier 1 — Metadata_ (always loaded): name + description, ~100 tokens.
- _Tier 2 — Instructions_ (loaded when activated): the SKILL.md body, ideally <500 lines.
- _Tier 3 — References, scripts, assets_ (loaded on demand): full schemas, error tables, validation scripts, sample payloads.

**Composability.** Complex flows are built by composing atomic skills, not by writing a mega-skill. An integration orchestrator references API skills; API skills reference foundation skills. Knowledge flows in one direction.

### 3.2 Skill Types

Two complementary archetypes, both needed:

**Reference skills** are atomic — they answer "how do I call this API?" or "how does this concern work?". Tightly scoped. The bulk of the bank is reference skills.

> Examples: `order-create`, `txns`, `webhooks-and-signatures`.

**Orchestrator skills** are workflow recipes — they compose reference skills into end-to-end merchant journeys. They own the _narrative_; references own the _details_.

> Examples: `hyper-checkout`, `express-checkout-sdk`, `express-checkout-backend`.

Orchestrators must not duplicate reference content. They link to references as building blocks. This is the discipline that keeps the bank DRY.

### 3.3 The Multi-Axis Problem and How We Resolve It

Payment skills can legitimately be grouped along several axes:

- **Axis A — Payment Flow / Instrument:** cards, UPI Intent, UPI Collect, wallets, mandates, pre-auth, decoupled.
- **Axis B — Integration Pattern:** backend-only, hybrid SDK, hosted/redirect.
- **Axis C — API Operation / Lifecycle Stage:** initiate, authorize, capture, refund, query, void.
- **Axis D — Cross-Cutting Concerns:** auth, idempotency, webhooks, error handling.

**The resolution:** rather than picking one axis, we pick a primary axis per layer.

- Foundations are organized by Axis D.
- API References are organized by Axis C (one skill per API operation), with Axis A folded in as variants inside each API skill.
- Integrations are organized by Axis B.

This means a payment flow like "mandate" doesn't get its own folder — it appears as a variant section inside `order-create`, `txns`, and any other API it modifies. The API reference is the single source of truth for the payload, and the variant sections explain how the payload changes for that flow.

### 3.4 Splitting vs. Merging Heuristics

A common failure mode is making skills too coarse or too fine.

**Make it ONE skill if** the agent would always need both pieces together to ship working code, the request/response shape is the same across variants, or the differences are configuration parameters rather than behavioral changes.

**Make it TWO skills if** a merchant could legitimately want one without the other, the schemas differ meaningfully, the error model or webhook events differ, or activation triggers are clearly distinct.

**Rule of thumb:** if you can't write a single, non-compound `Use when…` clause, split it.

### 3.5 Naming Conventions

| Element                      | Convention                                       | Example                                                                                                            |
| ---------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Folder name                  | `kebab-case`, max 64 chars, matches `name` field | `order-create`                                                                                                     |
| `name:` field in frontmatter | Same as folder name                              | `order-create`                                                                                                     |
| Description start            | One imperative sentence describing the outcome   | "Create a Juspay order to initiate a payment."                                                                     |
| Activation clause            | Mandatory `Use when…` with intent + keywords     | "Use when the merchant needs to start a new payment, mentions order creation, or asks how to begin a transaction." |

Avoid vague verbs (`process`, `handle`, `manage`), compound names (`create-and-capture-order`), and provider-internal jargon in descriptions.

---

## 4. The SKILL.md Anatomy

Every skill follows the Agent Skills Specification: a folder containing a `SKILL.md` with YAML frontmatter, plus optional `references/`, `scripts/`, and `assets/` subdirectories.

```text
skill-name/
├── SKILL.md                       # required: frontmatter + instructions
├── references/                    # optional: deep-dive docs loaded on demand
├── scripts/                       # optional: deterministic helpers, validators
└── assets/                        # optional: templates, sample payloads
```

The `SKILL.md` body should stay under ~500 lines. Anything longer goes into `references/` and is linked from the body.

Standard sections inside a `SKILL.md`:

- **When to use** — the activation context in plain language.
- **Prerequisites** — links to foundation skills and any other skills that must be read first.
- **Core content** — the actual instructions: schemas, steps, decision points.
- **Common errors** — top failures with remediation. Full error tables go in `references/`.
- **Related skills** — links to upstream and downstream skills (what calls this, what this calls).

For API reference skills specifically, the core content should document the _full superset schema_ with conditional fields marked by flow variant (e.g., "this field is required for mandate flows, optional otherwise"). Integration orchestrators specify which subset of fields to populate.

---

## 5. Folder Structure

```text
skills/
├── SKILL.md                          # bank-level entry point: how to navigate
│
├── foundations/
│   ├── authentication/
│   ├── idempotency-and-retries/
│   ├── webhooks-and-signatures/
│   ├── error-model/
│   └── sandbox-and-testing/
│
├── api-references/
│   ├── order-create/
│   ├── session/
│   ├── txns/
│   ├── create-customer/
│   └── ...                           # one folder per Juspay API
│
├── integrations/
│   ├── hyper-checkout/
│   ├── express-checkout-sdk/
│   └── express-checkout-backend/
│
└── go-live/
    └── production-readiness-checklist/
```

### 5.1 What each layer owns

**`SKILL.md` (bank root)** — orients the agent. Tells it the navigation model: start with the integration type the merchant wants, follow links to API References as needed, always read Foundations first, and check Go-Live before production.

**`foundations/`** — cross-cutting concerns shared by every integration and every API. Every other skill in the bank links here in its Prerequisites section instead of restating the content. When auth or idempotency rules change, this is the only place that needs updating.

**`api-references/`** — one skill per Juspay API, treated as the single source of truth for that API's request and response schema. Documents the full superset of fields, with payment-flow variants (mandates, decoupled card transactions, pre-auth, etc.) folded in as conditional sections within the same skill. Activation triggers point to the API name and the merchant-facing operation.

**`integrations/`** — the three integration-type orchestrators. Each one owns the _sequence of API calls_, the _decision points_ (e.g., when to call `txns` vs. when the SDK handles it), and the _integration-specific gotchas_. None of them own API payload details — those are always delegated to `api-references/`. Activation triggers match the merchant's first decision: "which integration shape do I want?"

**`go-live/`** — production-readiness skill. A checklist that helps a merchant validate their integration end-to-end before flipping the switch: webhook signatures verified, idempotency keys in place, error handling covers terminal vs. retryable cases, sandbox-tested across success and failure paths, monitoring and alerting hooked up.

### 5.2 The contract between layers

This is the discipline that keeps the bank healthy:

| Layer                 | Owns                                                                      | Delegates                                                               |
| --------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Bank-level `SKILL.md` | Navigation, taxonomy                                                      | Everything else                                                         |
| `foundations/`        | Cross-cutting mechanics                                                   | Nothing — these are leaves                                              |
| `api-references/`     | Full payload schemas, response shapes, error codes per API, flow variants | Auth, idempotency, webhooks (→ foundations)                             |
| `integrations/`       | Sequence, integration-specific decisions, UI/UX boundaries                | API payloads (→ api-references), cross-cutting concerns (→ foundations) |
| `go-live/`            | Pre-launch validation steps                                               | Implementation details (→ everywhere else)                              |

A useful test: if you find yourself writing API payload fields inside an integration orchestrator, stop. That content belongs in `api-references/`, and the orchestrator should link to it.

### 5.3 Inside an API reference skill (with flow variants folded in)

```text
api-references/order-create/
├── SKILL.md                       # full superset schema + variant sections
├── references/
│   ├── full-schema.json           # complete request/response schema
│   ├── error-codes.md             # exhaustive error table
│   └── flow-variants/
│       ├── mandate.md             # how the payload changes for mandates
│       ├── decoupled-card.md      # how it changes for decoupled cards
│       └── pre-auth.md            # how it changes for pre-auth
├── scripts/
│   └── validate-request.py
└── assets/
    └── sample-payloads/
```

The `SKILL.md` body summarizes the API and points the agent to the relevant variant file based on the merchant's flow. The agent loads only the variant it needs.

### 5.4 Inside an integration orchestrator skill

```text
integrations/hyper-checkout/
├── SKILL.md                       # sequence + decisions, no payload details
├── references/
│   ├── sequence-diagram.md        # end-to-end flow
│   ├── ui-customization.md        # what the merchant can theme/configure
│   └── platform-notes.md          # web vs mobile considerations
└── assets/
    └── sample-app/                # minimal end-to-end example
```

The `SKILL.md` reads like a recipe: "Step 1 — call `api-references/session` with these conditional fields populated. Step 2 — render the SDK. Step 3 — handle the callback by calling `api-references/order-status`. Throughout, follow `foundations/idempotency-and-retries/` and verify webhooks per `foundations/webhooks-and-signatures/`."

---

## 6. Authoring Quality Bar

Before any skill ships into the bank, verify:

- [ ] **Activation clarity** — a fresh agent can read only the description and correctly decide whether to load the skill.
- [ ] **Single responsibility** — the skill answers one question.
- [ ] **Self-contained context** — instructions assume only the foundation skills and the listed prerequisites.
- [ ] **Length budget** — `SKILL.md` under ~500 lines; everything else in `references/`.
- [ ] **Concrete examples** — at least one full request/response pair, ideally as a runnable curl or SDK snippet.
- [ ] **Error coverage** — top 5 most common failures named with remediation; full table in `references/`.
- [ ] **Idempotency story** — explicit guidance on safe retries (or a link to the foundation skill).
- [ ] **Webhook story** — which events fire, in what order, and how to verify them (or a link to foundations).
- [ ] **Sandbox parity** — how to test end-to-end without real money.
- [ ] **Linked siblings** — the "Related skills" section points to upstream and downstream skills.
- [ ] **Layer contract honored** — the skill doesn't reach into another layer's territory (e.g., orchestrators don't redocument payloads).
- [ ] **Tested with two agents** — one author-agent helps refine the skill; a second fresh agent attempts the integration using only the skill.

---

## 7. Phasing

**Phase 1 — Ship the spine.**

- Bank-level `SKILL.md`.
- Stub `foundations/authentication/` and `foundations/webhooks-and-signatures/` (the two every integration needs on day one).
- The three integration orchestrators (`hyper-checkout`, `express-checkout-sdk`, `express-checkout-backend`).
- The API reference skills they call out to (Order Create, Session, Txns, Create Customer, and any others on the critical path).

**Phase 2 — Deepen.**

- Remaining `foundations/` (idempotency, error model, sandbox).
- Flow variant sections inside each API reference (mandates, decoupled, pre-auth, etc.).
- Remaining API reference skills.

**Phase 3 — Production readiness and polish.**

- `go-live/production-readiness-checklist/`.
- Sample apps in each integration's `assets/`.
- A/B testing the bank with fresh agents and iterating on activation triggers.

---

## 8. Summary

1. **Goal:** teach AI coding agents to integrate Juspay correctly the first time.
2. **Insight:** APIs and flows are stable building blocks; integration types are orchestrators.
3. **Layers:** foundations, API references, integrations, go-live, bank entry point.
4. **Discipline:** strict layer contracts — orchestrators delegate payloads to API References, everyone delegates cross-cutting concerns to Foundations.
5. **Flows folded in:** payment flows are variants inside API references, not standalone skills.
6. **Progressive disclosure:** metadata always, instructions on activation, references on demand.
7. **Quality bar:** every skill passes the authoring checklist and is validated by a second, fresh agent.

---

## References

- Anthropic — Agent Skills documentation: https://docs.claude.com/en/docs/claude-code/skills
- Agent Skills Specification: https://github.com/agentskills/agentskills
- Stripe AI / Skills: https://github.com/stripe/ai
- Stripe — Build on Stripe with AI: https://docs.stripe.com/agents
- PayPal Agent Toolkit: https://github.com/paypal/agent-toolkit
- PhonePe PG Skills: https://github.com/PhonePe/phonepe-pg-skills
- Microsoft — Agent Skills (VS Code / Copilot): https://learn.microsoft.com/copilot

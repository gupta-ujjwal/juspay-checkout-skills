# Phase 1 learnings — `juspay-checkout-skills` (superseded)

> **Superseded by [`docs/framework.md`](./docs/framework.md) on 2026-05-10.**
>
> The structural decisions in this file (flow-primary slicing, `_base/` + `flows/` + `integrations/` layout, `merchant-config.yml` machinery, `.verifications.yml` provenance file, `type:`/`applies_to:` schema fields) are no longer authoritative. The bank now follows the framework's five-layer architecture (`foundations/`, `api-references/`, `integrations/`, `go-live/`, bank-level `SKILL.md`); flow-variant sections and merchant-gate placement are deferred to Phase 2.
>
> **What's still load-bearing below:** the doc-vs-code findings (`OrderStatus` has 22 values, `FEATURE_NOT_ENABLED` returns HTTP 400, `OrderCreateRequest` declares every field as `Maybe`), the file:line table at the bottom (still ground truth for Phase 1 api-references), and the workflow learnings (hickey/lowy timing observations, the `apm install` regeneration gotcha, the PyYAML-over-hand-rolled-state-machine lesson).

---

## Original captured notes

Captured 2026-05-08 after `feat/phase1-base-and-cards-3ds` was reverted. The branch built and shipped a complete EC-API end-to-end slice, then we decided to step back and re-cement the integration approaches before authoring skills. This file condenses what we learned so we don't re-litigate it.

The reverted PR (kept for reference): https://github.com/gupta-ujjwal/juspay-checkout-skills/pull/1 — it carries the actual cards, validator code, and the full Hickey/Lowy + code-police comments worth re-reading before drafting Phase 2.

---

## Decisions that should survive the rewrite

These came out of the talk-mode evaluation + Hickey + Lowy review and held up through implementation. Treat as defaults; only re-open with new evidence.

### Slicing is flow-primary, not platform×flow

The original CLAUDE.md plan put platform variance in the directory hierarchy:

```text
hyper-checkout/{android,ios,web,react-native}/
express-checkout-sdk/{android,ios,react-native,flutter,cordova,capacitor}/
express-checkout-api/{cards_3ds, ...13 flows}.md
```

That fragments **one** business concept ("card 3DS payment") across up to 11 cards. We replaced it with:

```text
juspay-checkout-skill/
├── _base/                # cross-cutting cards (auth, environments, order_create, ...)
├── flows/                # one card per business flow with conditional
│                         # ### EC-API / ### HyperCheckout / ### EC-SDK subsections
└── integrations/         # Phase 3: one card per mode, with platform subsections inside
                          # (HC × {Android,iOS,Web,RN}; EC-SDK × {6 platforms}; EC-API)
```

**Why this seam.** Lowy's volatility check landed: payment flows ("create order → 3DS → poll → fulfill") have a stable orchestration that doesn't change across modes. The _payload_ shapes do change (form-encoded `/orders` vs JSON `/txns` vs hosted-page session). Putting payloads in per-mode subsections inside the flow card preserves the orchestration as the durable artefact while letting payload differences live where they happen.

**Phase 3 extraction caveat.** When HC/EC-SDK subsections get fully populated (Phase 3), reviewers shouldn't have to hold three payload grammars in their head simultaneously. Plan: extract per-mode payloads to `integrations/<mode>.md` at that point, leaving the flow card with one-line cross-references. We documented this in CLAUDE.md before tearing the branch down — see commit `80a0aaa` if needed.

### Single-mode vs multi-mode flows are different

`refund.md` is EC-API-only — refunds are server-to-server regardless of how the original payment was collected. The card has no per-mode subsections; the whole card _is_ the EC-API content. Don't force every flow card into the multi-mode template.

### Merchant-gate enforcement is structural, not a behaviour rule

The original plan said _"AI must ask the merchant to confirm before generating code"_ — a behaviour rule with no structural enforcement. We replaced it with three coordinated artefacts:

- **`merchant-config.yml.example`** — per-merchant gate state. Merchants copy to `merchant-config.yml` (gitignored), fill `true` / `false` / `unknown` per gate.
- **`_base/merchant_gates.md`** — explains the gating model + lists the gates with their loud/silent failure mode, mapped from `merchant-config.yml.example` keys to upstream `MerchantAccount` fields.
- **`scripts/check.py`** — validates that any gate-shaped keyword referenced in a card's `## Merchant Enablement` section resolves against `merchant-config.yml.example`.

**`unknown` is the friction by design.** A gate that hasn't been confirmed forces the agent to ask once; setting it to `true` or `false` short-circuits future prompts.

**Loud vs silent gates** is the load-bearing distinction:

- **Loud** — API rejects with `FEATURE_NOT_ENABLED`. Detectable at runtime.
- **Silent** — feature is omitted from the response with no error. _Undetectable at runtime._ Only the up-front config check catches these. This is why `merchant-config.yml` exists — silent gates can't be deferred to "we'll handle the error path."

**Four gates are intentionally NOT in `merchant-config.yml.example`** because they aren't agent-configurable booleans:

- `mandateConfig` — JSON blob, not a boolean
- `basiliskKeyId` / `encryptionKeyIds` — JWE key material
- `enabled` — master kill-switch, not merchant-toggleable
- `enableSuccessRateBasedGatewayElimination` — internal tuning, set by Juspay

Document this delta in both files when re-introducing them.

### Provenance lives in `.verifications.yml`, not per-card frontmatter

We initially put `verified_against: euler-workspace-5 (2026-05-07 snapshot)` in every card's frontmatter `metadata` block. Lowy's volatility lens flagged it: provenance timestamps drift on a different axis from card content. Bulk re-verification touches every card; per-card frontmatter forces the timestamp to live next to the content even though they don't change together.

The fix was a `.verifications.yml` at repo root with one entry per skill ID:

```yaml
auth_basic:
  verified_at: "2026-05-07"
  source: euler-workspace-5
```

Cards retain only the `references:` list (public docs that merchants can resolve). `scripts/check.py` cross-validates that every `dependencies.yml` ID has a `.verifications.yml` entry.

### Code beats docs, and the pattern proved out

For every claim in a Phase 1 card we cited a `file:line` in `~/juspay/euler-workspace-5/`. Three concrete examples where the code disagreed with public docs:

- `OrderCreateRequest` declares **every** field as `Maybe` — the typed signature alone says nothing about what's required. Validation logic in the request handler is the source of truth.
- `FEATURE_NOT_ENABLED` returns HTTP **400**, not 403 as the explorer subagent (and some public docs) claimed. Verified at `PredefinedErrors.hs:161`.
- `OrderStatus` enum has **22** values; public docs typically list ~12. The full set lives at `External/Order.hs:19`.

The doc-fetch recipe (append `.md` to any juspay.io docs URL) is useful as a starting point but never as authority.

### `dependencies.yml` is the registry; inline `## Dependencies` is the per-card declaration

Different consumers, different volatility. The registry is for tooling (rename detection); the inline declaration is for the agent at load time. Keep separate.

### Schema drift isn't a maintainer problem — it's a CI problem

We had two near-misses where CLAUDE.md's schema example showed fields that no longer existed in real cards (`verified_against:` after the move to `.verifications.yml`; `applies_to: [hyper-checkout/android, ec-api]` after the slicing change). For the rewrite, consider validating CLAUDE.md's schema example against `scripts/check.py`'s parser — if the example doesn't pass the validator, it's wrong.

---

## What we'd do differently (open for discussion)

These are the points worth re-evaluating before writing cards.

### Audience-complecting in the schema

Each card today serves three audiences in one file:

- **Agent code-gen** — `When to Apply`, `Endpoints`, `Request/Response`, `Common AI Mistakes`
- **Maintainer verification** — `metadata`, `references:`, code traceback (now in `.verifications.yml` but the references prose still mixes in)
- **Merchant config awareness** — `Merchant Enablement` section

We tracked a Phase 5 split (per-card `.verification.md` companion file) but didn't ship it. **Decision needed**: is the audience split worth doing earlier, or is the cost of cross-linking two files per skill worse than the audience-mixing? PhonePe's analogue (`/tmp/phonepe-pg-skills/`, 5 cards) doesn't split — but they have less surface area.

### Multi-mode subsections vs. integration-mode adapters

We chose mode-as-conditional-subsections-inside-flow over mode-as-thin-adapters. Lowy's later finding (the Phase 3 extraction note) was that the inline approach strains when multiple modes get fully populated. **Decision needed**: should Phase 2 already pre-stage the `integrations/<mode>.md` extraction so flow cards don't accumulate per-mode payload chunks that have to move later? Or is the Phase 3 extraction cheap enough?

### Stub-detection convention

`scripts/check.py` recognised Phase-N stubs via a regex on `> **Phase \d+**` as the first non-empty line of a `### Mode integration` subsection. That's fragile — anyone who writes the stub differently breaks the heuristic. **Decision needed**: do we want a proper `<!-- stub -->` marker, a frontmatter field listing populated modes, or accept the fragility as Phase 1 was small enough not to matter?

### The schema is too heavy for some cards

Many base cards (e.g. `environments`, `auth_basic`) genuinely don't need `Execution Flow`, `Merchant Enablement`, `Implementation Checklist`. Phase 1 made these conditional but the heaviness was real. **Decision needed**: split the schema by card type (base vs flow), or keep one schema with conditional sections enforced by the validator?

### `applies_to: [ec-api]` is awkwardly redundant for single-mode flows

For `refund.md`, `applies_to: [ec-api]` and the absence of any `### Mode integration` subsection said the same thing twice. The validator special-cased single-mode to avoid the false-positive. **Decision needed**: drop `applies_to` entirely for single-mode flows (let the validator infer), or keep it consistent across all flow cards?

### The test/CI infrastructure was zero

`.agency/do.md`'s test command was `echo 'no tests yet'`. `scripts/check.py` had no unit tests — its parser was hand-verified. For the rewrite, scaffolding a small test suite (`tests/test_check.py` with fixtures of valid/invalid cards) is worth doing before the validator gets more behaviour.

---

## Tooling that worked well

Reuse these without re-deriving.

### `scripts/check.py` shape

The final shape was:

- PEP 723 inline metadata (`# /// script ... ///`) for the `PyYAML` dep so `uv run scripts/check.py` auto-installs.
- `parse_dependencies_yml`, `parse_verifications_yml`, `parse_merchant_config_keys` each return `(set, errors)` so malformed shapes surface at parse-time.
- Cross-checks driven by a `[(set_diff, error_template)]` table.
- `_suggest_gate_keys` uses `difflib.get_close_matches(cutoff=0.75)` so typoed gate names flag as errors but unrelated tokens (`unique_request_id`) skip silently.

The whole file was ~330 lines after `code-police`'s `prefer-focused-library` swap to PyYAML. Without the swap it was ~430 lines of hand-rolled state-machine parsing. Don't hand-roll YAML parsing again.

### apm-managed `.claude/rules/conventions.md`

The repo uses APM. `.claude/rules/conventions.md` is **generated** from `.apm/instructions/conventions.instructions.md` by `apm install`. Edits to the generated file get overwritten — always edit the `.apm/` source, then run `apm install`.

This bit me twice during the workflow. Note the warning at the top of `.claude/rules/apm-sources.md` — it's not just for show.

### `/do` workflow timing observations

From the timing summary on the reverted PR:

- **`hickey+lowy`** was the dominant step at ~39% of total. The reviewers ran on ~2000 lines of new content (mostly Markdown). Most of that didn't bite the same way code reviews do — the structural decisions (slicing, schema, gate model) bit hard, the card prose didn't. For Phase 2, scope reviewer prompts to structural deltas + `scripts/check.py` only.
- **`docs`** caught most drift but missed the schema example in CLAUDE.md (which `police` later cleaned up). Adding a CLAUDE.md self-validation check to `scripts/check.py` would catch this in `check`.
- The per-finding-per-commit rule produced clean PR history but added ~30s of bash overhead per commit. It's a deliberate cost; budget for it.

### Hickey/Lowy review prompt shape that worked

Reviewing a sketch (talk mode) and reviewing the diff (post-implement) produced different findings:

- **Sketch review** caught the slicing decision (drop `platforms/` matrix) and the audience-complecting concern.
- **Diff review** caught silent gate-skip in the validator, missing schema headers, parse-site error surfacing, the suffix-coupled gate regex.

Both passes were valuable. Don't try to merge them.

---

## Source-of-truth file:line references worth keeping

These are validated reference points for the rewrite:

| What                                      | Where (`euler-workspace-5/`)                                    |
| ----------------------------------------- | --------------------------------------------------------------- |
| Order create handler                      | `euler-api-order/src/Euler/Server.hs:3073`                      |
| `OrderCreateRequest` record (100+ fields) | `euler-api-order/src/Euler/API/Order.hs:150`                    |
| `OrderStatusRequest`                      | `euler-api-order/src/Euler/API/Order.hs:1289`                   |
| `OrderStatus` enum (22 values)            | `euler-db/src/Euler/DB/Common/Types/External/Order.hs:19`       |
| `OrderStatus` → numeric id mapping        | same file, `orderStatusToInt`                                   |
| Predefined errors                         | `euler-api-order/src/Euler/Common/Errors/PredefinedErrors.hs`   |
| Refund routes                             | `euler-api-txns/src/Euler/API/Txns/Server.hs:212-240`           |
| Txn intent create request                 | `euler-api-order/src/Euler/API/TxnIntent.hs:27`                 |
| Encrypted (signature-authed) order create | `euler-api-order/src/Euler/Server.hs:927`                       |
| Verified merchant gates                   | `euler-db/src/Euler/DB/Storage/Types/MerchantAccount.hs:60-216` |

The Phase 1 PR's `research` step output captures more — re-read the `git show 9a55ae8` commit body or the PR's research-step verification text.

---

## Pointers back to the reverted work

If we want to crib content rather than re-write from scratch:

- `git log origin/main..feat/phase1-base-and-cards-3ds` (if the branch is still around locally)
- The PR diff: https://github.com/gupta-ujjwal/juspay-checkout-skills/pull/1/files
- Specific commits worth re-reading:
  - `9a55ae8` — initial Phase 1 implementation
  - `5480939` — `.verifications.yml` extraction
  - `55d6af2` — PyYAML swap
  - `292c181` — `applies_to` cross-validation
  - `80a0aaa` — Phase 3 extraction tracking note in CLAUDE.md

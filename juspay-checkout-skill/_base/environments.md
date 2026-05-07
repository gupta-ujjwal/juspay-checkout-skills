---
name: environments
description: Sandbox and production hosts for every Juspay Checkout endpoint
type: base
metadata:
  author: Juspay
  version: "0.1.0"
  verified_against: euler-workspace-5 (2026-05-07 snapshot)
references:
  - https://juspay.io/sea/docs/ec-api-global/docs/getting-started/environments.md
---

## When to Apply

- Choosing the host for any Juspay API call.
- Deciding which credentials to use (sandbox keys vs production keys).

## Hosts

| Environment | Host                        | Use for                                                             |
| ----------- | --------------------------- | ------------------------------------------------------------------- |
| Sandbox     | `https://sandbox.juspay.in` | Integration testing. Credentials issued separately from production. |
| Production  | `https://api.juspay.in`     | Live merchant traffic.                                              |

The same path layout serves both. There is **no separate path prefix** for sandbox — the host is the only difference. (The `/ecr` prefix that appears in some internal references is stripped by the edge proxy and is not part of public paths.)

## Request

Both environments require the same auth schemes. See `auth_basic` for the default scheme.

## Common AI Mistakes

### Field naming and gotchas

- Sandbox credentials and production credentials are **not interchangeable**. Each issues its own merchant ID and API key.
- The `payment_page_environment` request field on order create is unrelated to the host — it is a Juspay internal value (`sandbox` / `production`) that Juspay uses to route gateway traffic, and may not match the host you call.

### Doc-vs-code disagreements

- Some legacy docs reference `https://api.juspay.in/ecr/...` paths. The `/ecr/` prefix is internal and stripped by the edge — use the path without it.

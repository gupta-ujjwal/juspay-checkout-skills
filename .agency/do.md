# /do config

## Check command
uv run scripts/check.py

## Format command
prettier --write '**/*.md'

## Test command
echo 'no tests yet'

## CI command
uv run scripts/check.py

## Documentation
Keep `README.md` and `juspay-checkout-skill/SKILL.md` in sync with user-facing changes
(new skill cards, slicing changes, schema changes). `CLAUDE.md` is for repo maintainers
and should be updated when the build/verify workflow changes — not on each card add.

<!-- Optional (add manually for the evidence step):
## PR evidence
-->

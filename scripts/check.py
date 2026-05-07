#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Validator for the juspay-checkout-skills bank.

Runs as the project's check + CI command (`.agency/do.md`):

    uv run scripts/check.py     # auto-installs PyYAML the first time

Or, if you have PyYAML system-installed: `python3 scripts/check.py`.

Validates:

1. Frontmatter — every `.md` skill card has a YAML frontmatter block with the
   required fields: `name`, `description`. Cards under `_base/` and `flows/`
   additionally need `type` (base|flow) and a non-empty `references:` list.
   The `name` field must match the filename (without extension).

2. Dependencies — for every skill card that has a `## Dependencies` section,
   each listed item must resolve to an entry in `dependencies.yml`.

3. Gate references — for every flow card that has a `## Merchant Enablement`
   section referencing a snake_case keyword, validate that any keyword close
   to a known gate matches one in `merchant-config.yml.example`. Catches typos
   without false-flagging incidental tokens like `unique_request_id`.

4. Provenance — every skill ID registered in `dependencies.yml` must have an
   entry in `.verifications.yml`, and vice versa.

5. Mode/heading consistency — flow cards' `applies_to` frontmatter must agree
   with the `### EC-API integration` / `### HyperCheckout integration` /
   `### Express Checkout SDK integration` subsection headings.

Exits 0 on success, 1 on any failure.
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO / "juspay-checkout-skill"
DEPS_FILE = REPO / "dependencies.yml"
MERCHANT_CONFIG = REPO / "merchant-config.yml.example"
VERIFICATIONS_FILE = REPO / ".verifications.yml"

MODE_HEADINGS: dict[str, str] = {
    "ec-api": "EC-API integration",
    "hyper-checkout": "HyperCheckout integration",
    "express-checkout-sdk": "Express Checkout SDK integration",
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a `---`-delimited YAML frontmatter block from its Markdown body
    and return (parsed_data, body). Raises ValueError if the delimiters are
    missing or the YAML is malformed.
    """
    if not text.startswith("---\n"):
        raise ValueError("missing opening `---` delimiter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("missing closing `---` delimiter")
    raw = text[4:end]
    body = text[end + 5 :]
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(f"frontmatter is not a mapping (got {type(data).__name__})")
    return data, body


def _suggest_gate_keys(keyword: str, gate_keys: set[str]) -> list[str]:
    """Return gate_keys that look like plausible "did you mean" candidates for
    `keyword`. Used to distinguish gate-name typos (where the offender shares
    structure with a real gate) from incidental snake_case tokens like
    `unique_request_id` that are not gate references at all."""
    return difflib.get_close_matches(keyword, gate_keys, n=3, cutoff=0.75)


def _load_yaml(path: Path) -> object:
    """Return the parsed YAML from `path`, or `None` if the file is missing."""
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


def parse_dependencies_yml(path: Path) -> tuple[set[str], list[str]]:
    """Collect every skill ID listed under any top-level key in dependencies.yml.
    Returns (ids, errors) — non-list top-level values are reported, not silently
    dropped, so a malformed registry surfaces as a clear error rather than as a
    misleading downstream 'orphan card' message."""
    data = _load_yaml(path)
    if data is None:
        return set(), []
    if not isinstance(data, dict):
        return set(), [f"{path.name}: top level must be a mapping"]
    ids: set[str] = set()
    errors: list[str] = []
    for key, value in data.items():
        if not isinstance(value, list):
            errors.append(
                f"{path.name}: top-level key `{key}` must be a list of skill IDs "
                f"(got {type(value).__name__})"
            )
            continue
        ids.update(str(item) for item in value if isinstance(item, str))
    return ids, errors


def parse_verifications_yml(path: Path) -> tuple[set[str], list[str]]:
    """Collect skill IDs registered in .verifications.yml. Each entry must be a
    mapping containing `verified_at`. Returns (ids, errors) — entries that are
    present but malformed (missing `verified_at`, wrong shape) surface as
    explicit errors rather than being silently excluded."""
    data = _load_yaml(path)
    if data is None:
        return set(), []
    if not isinstance(data, dict):
        return set(), [f"{path.name}: top level must be a mapping"]
    ids: set[str] = set()
    errors: list[str] = []
    for key, value in data.items():
        if not isinstance(value, dict):
            errors.append(
                f"{path.name}: entry `{key}` must be a mapping with `verified_at` "
                f"(got {type(value).__name__})"
            )
            continue
        if "verified_at" not in value:
            errors.append(
                f"{path.name}: entry `{key}` is missing required `verified_at` field"
            )
            continue
        ids.add(key)
    return ids, errors


def parse_merchant_config_keys(path: Path) -> set[str]:
    """Collect gate keys from merchant-config.yml.example's `gates:` block."""
    data = _load_yaml(path)
    if not isinstance(data, dict):
        return set()
    gates = data.get("gates")
    if not isinstance(gates, dict):
        return set()
    return set(gates.keys())


def extract_section(body: str, heading: str) -> str | None:
    """Return the content of a `## <heading>` section up to the next `## ` or EOF."""
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    m = pattern.search(body)
    if not m:
        return None
    start = m.end()
    next_m = re.search(r"^##\s+", body[start:], re.MULTILINE)
    end = start + next_m.start() if next_m else len(body)
    return body[start:end]


def extract_dependency_ids(deps_section: str) -> list[str]:
    r"""Parse `- skill_id` lines from a Dependencies section's content. Strips
    inline backticks so `- \`auth_basic\`` and `- auth_basic` both work."""
    ids: list[str] = []
    for raw_line in deps_section.splitlines():
        m = re.match(r"\s*-\s*`?([A-Za-z_][\w]*)`?\s*$", raw_line)
        if m:
            ids.append(m.group(1))
    return ids


def _check_applies_to_consistency(rel: Path, front: dict, body: str) -> list[str]:
    """For flow cards, every mode in `applies_to` must have a correspondingly-
    titled `### <Mode>` integration subsection in the body, and every such
    subsection that is *not* a Phase-N stub must have its mode listed in
    `applies_to`. Stubs are subsections whose first non-empty line is a
    `> **Phase N.**` blockquote — forward-reference signposts that don't yet
    require `applies_to` coverage.
    """
    errors: list[str] = []
    applies_to = front.get("applies_to", [])
    if not isinstance(applies_to, list):
        return [f"{rel}: `applies_to` must be a list"]

    multi_mode = len(applies_to) > 1
    for mode in applies_to:
        if mode not in MODE_HEADINGS:
            errors.append(
                f"{rel}: `applies_to` lists unknown mode `{mode}` "
                f"(expected one of: {', '.join(MODE_HEADINGS)})"
            )
            continue
        if not multi_mode:
            continue  # single-mode flow has no per-mode subsection — whole card is the mode
        heading = MODE_HEADINGS[mode]
        if not re.search(rf"^###\s+{re.escape(heading)}\s*$", body, re.MULTILINE):
            errors.append(
                f"{rel}: `applies_to` lists `{mode}` but no `### {heading}` heading found in body"
            )

    for mode, heading in MODE_HEADINGS.items():
        section_re = re.compile(
            rf"^###\s+{re.escape(heading)}\s*$\n(.*?)(?=^##?\s+|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = section_re.search(body)
        if not m:
            continue
        section_body = m.group(1).strip()
        first_nonempty = next(
            (line for line in section_body.splitlines() if line.strip()), ""
        )
        is_stub = bool(re.match(r"^>\s*\*\*Phase\s+\d+", first_nonempty))
        if is_stub:
            continue
        if mode not in applies_to:
            errors.append(
                f"{rel}: body has `### {heading}` with substantive content but "
                f"`applies_to` does not list `{mode}`"
            )

    return errors


def check_card(path: Path, valid_ids: set[str], gate_keys: set[str]) -> list[str]:
    errors: list[str] = []
    text = path.read_text()
    rel = path.relative_to(REPO)

    try:
        front, body = parse_frontmatter(text)
    except (ValueError, yaml.YAMLError) as e:
        return [f"{rel}: frontmatter parse error: {e}"]

    is_card = path.parent.name in {"_base", "flows"}

    required = ["name", "description"]
    if is_card:
        required += ["type", "references"]
    for key in required:
        if key not in front or front[key] in ("", None, [], {}):
            errors.append(f"{rel}: missing or empty frontmatter field `{key}`")

    if is_card:
        if front.get("name") != path.stem:
            errors.append(
                f"{rel}: frontmatter `name` ({front.get('name')!r}) does not match filename ({path.stem!r})"
            )
        if front.get("type") not in {"base", "flow"}:
            errors.append(
                f"{rel}: frontmatter `type` must be `base` or `flow` (got {front.get('type')!r})"
            )
        if not isinstance(front.get("references"), list) or not front["references"]:
            errors.append(f"{rel}: `references:` must be a non-empty list")

    if is_card and front.get("type") == "flow":
        errors.extend(_check_applies_to_consistency(rel, front, body))

    deps_section = extract_section(body, "Dependencies")
    if deps_section:
        for dep_id in extract_dependency_ids(deps_section):
            if dep_id not in valid_ids:
                errors.append(
                    f"{rel}: Dependencies references unknown skill id `{dep_id}` "
                    f"(not in dependencies.yml)"
                )

    enablement = extract_section(body, "Merchant Enablement")
    if enablement:
        if not gate_keys:
            errors.append(
                f"{rel}: Merchant Enablement section present but "
                f"merchant-config.yml.example is missing or has no gates: block — "
                f"gate references cannot be validated"
            )
        else:
            referenced = {
                kw
                for kw in re.findall(r"`([a-z][a-z0-9_]*)`", enablement)
                if "_" in kw  # exclude single-word backticks like `true`/`false`
            }
            for keyword in referenced:
                if keyword in gate_keys:
                    continue
                close = _suggest_gate_keys(keyword, gate_keys)
                if not close:
                    continue  # unrelated snake_case token, not a gate reference
                errors.append(
                    f"{rel}: Merchant Enablement references gate `{keyword}` not in "
                    f"merchant-config.yml.example "
                    f"(similar: {', '.join(close)})"
                )

    return errors


def main() -> int:
    if not SKILL_ROOT.exists():
        print(f"error: skill root {SKILL_ROOT} does not exist", file=sys.stderr)
        return 1

    valid_ids, dep_errors = parse_dependencies_yml(DEPS_FILE)
    gate_keys = parse_merchant_config_keys(MERCHANT_CONFIG)
    verified_ids, ver_errors = parse_verifications_yml(VERIFICATIONS_FILE)

    errors: list[str] = list(dep_errors) + list(ver_errors)
    cards: list[Path] = []
    for path in sorted(SKILL_ROOT.rglob("*.md")):
        cards.append(path)
        errors.extend(check_card(path, valid_ids, gate_keys))

    if not cards:
        errors.append(f"no skill cards found under {SKILL_ROOT.relative_to(REPO)}")

    declared_ids = {p.stem for p in cards if p.parent.name in {"_base", "flows"}}
    for missing in sorted(valid_ids - declared_ids):
        errors.append(f"dependencies.yml lists `{missing}` but no card exists for it")
    for orphan in sorted(declared_ids - valid_ids):
        errors.append(f"card `{orphan}` exists but is not registered in dependencies.yml")
    for unverified in sorted(valid_ids - verified_ids):
        errors.append(
            f"skill `{unverified}` is in dependencies.yml but has no entry in .verifications.yml"
        )
    for stray in sorted(verified_ids - valid_ids):
        errors.append(
            f".verifications.yml lists `{stray}` but it is not in dependencies.yml"
        )

    if errors:
        print(f"check.py: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(
        f"check.py: ok ({len(cards)} cards, {len(valid_ids)} registered ids, "
        f"{len(verified_ids)} verified ids, {len(gate_keys)} gate keys)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validator for the juspay-checkout-skills bank.

Runs as the project's check command (`.agency/do.md`).

Validates:

1. Frontmatter — every `.md` skill card has a YAML frontmatter block with the
   required fields: `name`, `description`, `metadata.verified_against`. Cards
   under `_base/` and `flows/` additionally need `type` (base|flow) and a
   non-empty `references:` list. The `name` field must match the filename
   (without extension).

2. Dependencies — for every skill card that has a `## Dependencies` section,
   each listed item must resolve to an entry in `dependencies.yml`. Catches
   typos and renames before they ship.

3. Gates — for every flow card that has a `## Merchant Enablement` section
   referencing a gate keyword (e.g. `refunds_in_dashboard_enabled`), that
   keyword must exist in `merchant-config.yml.example` so consumers know it.

Exits 0 on success, 1 on any failure. Stdlib only — no external deps.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO / "juspay-checkout-skill"
DEPS_FILE = REPO / "dependencies.yml"
MERCHANT_CONFIG = REPO / "merchant-config.yml.example"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Hand-parse YAML frontmatter for the limited shape this repo uses.

    Supports: top-level scalars, top-level lists (one item per line with `-`),
    one level of nested mappings (e.g. `metadata:` block). Quoted and unquoted
    string values both work. Returns (data, body) or raises ValueError.
    """
    if not text.startswith("---\n"):
        raise ValueError("missing opening `---` delimiter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("missing closing `---` delimiter")
    raw = text[4:end]
    body = text[end + 5 :]

    data: dict = {}
    current_key: str | None = None
    current_kind: str | None = None
    for raw_line in raw.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("  "):
            inner = raw_line[2:]
            if current_key is None:
                raise ValueError(f"indented line with no parent key: {raw_line!r}")
            if current_kind == "list":
                m = re.match(r"\s*-\s*(.*)$", inner)
                if not m:
                    raise ValueError(f"expected list item: {raw_line!r}")
                data[current_key].append(_strip_quotes(m.group(1).strip()))
            elif current_kind == "map":
                m = re.match(r"([A-Za-z_][\w]*):\s*(.*)$", inner)
                if not m:
                    raise ValueError(f"expected key:value in map: {raw_line!r}")
                k, v = m.group(1), m.group(2).strip()
                data[current_key][k] = _strip_quotes(v)
            else:
                raise ValueError(f"unexpected indented content: {raw_line!r}")
            continue

        m = re.match(r"([A-Za-z_][\w]*):\s*(.*)$", raw_line)
        if not m:
            raise ValueError(f"unrecognised line: {raw_line!r}")
        key, value = m.group(1), m.group(2).strip()
        if value == "":
            data[key] = {}
            current_key = key
            current_kind = "map"
        elif value.startswith("["):
            inner = value.strip("[]")
            data[key] = [_strip_quotes(item.strip()) for item in inner.split(",") if item.strip()]
            current_key = key
            current_kind = "list-inline"
        else:
            data[key] = _strip_quotes(value)
            current_key = key
            current_kind = "scalar"
        if value == "" and key in {"references"}:
            data[key] = []
            current_kind = "list"
    return data, body


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def parse_dependencies_yml(path: Path) -> set[str]:
    """Collect skill IDs from dependencies.yml. Ignores comments and blank lines."""
    ids: set[str] = set()
    if not path.exists():
        return ids
    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        m = re.match(r"\s*-\s*([A-Za-z_][\w]*)\s*$", line)
        if m:
            ids.add(m.group(1))
    return ids


def parse_merchant_config_keys(path: Path) -> set[str]:
    """Collect gate keys from merchant-config.yml.example."""
    keys: set[str] = set()
    if not path.exists():
        return keys
    in_gates = False
    for raw_line in path.read_text().splitlines():
        if raw_line.startswith("gates:"):
            in_gates = True
            continue
        if in_gates:
            if raw_line and not raw_line.startswith((" ", "\t", "#")):
                in_gates = False
                continue
            m = re.match(r"\s+([A-Za-z_][\w]*):\s*", raw_line)
            if m:
                keys.add(m.group(1))
    return keys


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


def check_card(path: Path, valid_ids: set[str], gate_keys: set[str]) -> list[str]:
    errors: list[str] = []
    text = path.read_text()
    rel = path.relative_to(REPO)

    try:
        front, body = parse_frontmatter(text)
    except ValueError as e:
        return [f"{rel}: frontmatter parse error: {e}"]

    is_card = path.parent.name in {"_base", "flows"}

    required = ["name", "description"]
    if is_card:
        required += ["type", "metadata", "references"]
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
        meta = front.get("metadata", {})
        if not isinstance(meta, dict) or "verified_against" not in meta or not meta["verified_against"]:
            errors.append(f"{rel}: missing `metadata.verified_against`")
        if not isinstance(front.get("references"), list) or not front["references"]:
            errors.append(f"{rel}: `references:` must be a non-empty list")

    deps_section = extract_section(body, "Dependencies")
    if deps_section:
        for dep_id in extract_dependency_ids(deps_section):
            if dep_id not in valid_ids:
                errors.append(
                    f"{rel}: Dependencies references unknown skill id `{dep_id}` "
                    f"(not in dependencies.yml)"
                )

    enablement = extract_section(body, "Merchant Enablement")
    if enablement and gate_keys:
        for keyword in re.findall(r"`([a-z_][a-z0-9_]+_enabled|[a-z_][a-z0-9_]*_2fa)`", enablement):
            if keyword in gate_keys:
                continue
            close = [k for k in gate_keys if keyword in k or k in keyword]
            errors.append(
                f"{rel}: Merchant Enablement references gate `{keyword}` not in "
                f"merchant-config.yml.example"
                + (f" (similar: {', '.join(close)})" if close else "")
            )

    return errors


def main() -> int:
    if not SKILL_ROOT.exists():
        print(f"error: skill root {SKILL_ROOT} does not exist", file=sys.stderr)
        return 1

    valid_ids = parse_dependencies_yml(DEPS_FILE)
    gate_keys = parse_merchant_config_keys(MERCHANT_CONFIG)

    errors: list[str] = []
    cards: list[Path] = []
    for path in sorted(SKILL_ROOT.rglob("*.md")):
        cards.append(path)
        errors.extend(check_card(path, valid_ids, gate_keys))

    if not cards:
        errors.append(f"no skill cards found under {SKILL_ROOT.relative_to(REPO)}")

    declared_ids = {p.stem for p in cards if p.parent.name in {"_base", "flows"}}
    for missing in sorted(valid_ids - declared_ids):
        errors.append(
            f"dependencies.yml lists `{missing}` but no card exists for it"
        )
    for orphan in sorted(declared_ids - valid_ids):
        errors.append(
            f"card `{orphan}` exists but is not registered in dependencies.yml"
        )

    if errors:
        print(f"check.py: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"check.py: ok ({len(cards)} cards, {len(valid_ids)} registered ids, {len(gate_keys)} gate keys)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

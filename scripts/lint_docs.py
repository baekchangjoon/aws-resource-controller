"""Validate every markdown file under docs/ and inventory/ has a
well-formed YAML frontmatter, and every relative link resolves.

Exits non-zero on any failure. Used by CI; also runnable locally::

    python scripts/lint_docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FIELDS = {"title", "created", "updated", "status"}
LIVING_FIELDS = REQUIRED_FIELDS | {"phase", "reading_order"}
ALLOWED_STATUS = {"living", "snapshot", "superseded"}

# Docs we lint. CHANGELOG / CONTRIBUTING / LICENSE intentionally do not have
# frontmatter — they're not part of the docs/ taxonomy.
TARGETS = sorted(
    list(ROOT.glob("docs/*.md"))
    + list(ROOT.glob("docs/sessions/*.md"))
    + list(ROOT.glob("inventory/*.md"))
)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")


def _parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return yaml.safe_load(m.group(1)) or {}


def _check_fields(meta: dict, path: Path) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(meta)
    if missing:
        errors.append(f"missing frontmatter fields: {sorted(missing)}")
    status = meta.get("status")
    if status not in ALLOWED_STATUS:
        errors.append(f"status={status!r} not in {sorted(ALLOWED_STATUS)}")
    if status == "living":
        missing_living = LIVING_FIELDS - set(meta)
        if missing_living:
            errors.append(f"living doc missing extra fields: {sorted(missing_living)}")
    for date_field in ("created", "updated"):
        value = meta.get(date_field)
        if value is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(value)):
            errors.append(f"{date_field}={value!r} is not YYYY-MM-DD")
    return errors


def _check_links(text: str, path: Path) -> list[str]:
    errors: list[str] = []
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip()
        # Skip external URLs and mailto:.
        if "://" in target or target.startswith("mailto:"):
            continue
        # Resolve relative to the file's directory.
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            try:
                rel = resolved.relative_to(ROOT)
            except ValueError:
                rel = resolved
            errors.append(f"dead link: {target!r} → {rel} (does not exist)")
    return errors


def main() -> int:
    total_errors = 0
    for path in TARGETS:
        text = path.read_text()
        meta = _parse_frontmatter(text)
        errors: list[str] = []
        if meta is None:
            errors.append("missing or malformed YAML frontmatter")
        else:
            errors.extend(_check_fields(meta, path))
        errors.extend(_check_links(text, path))
        if errors:
            rel = path.relative_to(ROOT)
            print(f"✗ {rel}")
            for e in errors:
                print(f"    {e}")
            total_errors += len(errors)
        else:
            print(f"✓ {path.relative_to(ROOT)}")
    if total_errors:
        print(f"\n{total_errors} issue(s) across {len(TARGETS)} files")
        return 1
    print(f"\nall {len(TARGETS)} files clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())

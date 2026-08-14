from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("catalog_script", ROOT / "scripts" / "catalog.py")
assert SPEC is not None and SPEC.loader is not None
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)


def test_entries_match_schema_without_reports() -> None:
    assert catalog.check_catalog(require_reports=False) == []


def test_catalog_ids_are_unique() -> None:
    entries = catalog.load_entries()
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))


def test_find_entry_is_case_insensitive() -> None:
    entries = catalog.load_entries()
    entry = catalog._find_entry(entries, "WHNING0513/DEEPSEEK-SKILL-DOCTOR/DEEPSEEK-SKILL-DOCTOR")
    assert entry["name"] == "deepseek-skill-doctor"


def test_render_has_no_trailing_whitespace() -> None:
    output = catalog.render_catalog(catalog.load_entries())
    assert all(line == line.rstrip() for line in output.splitlines())

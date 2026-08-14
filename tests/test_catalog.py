from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

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


def test_install_from_local_git_repository_is_pinned_and_refuses_overwrite(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "source"
    bundle = repository / "skills" / "portable-example"
    second_bundle = repository / "skills" / "portable-second"
    bundle.mkdir(parents=True)
    second_bundle.mkdir(parents=True)
    (bundle / "SKILL.md").write_text(
        "---\n"
        "name: portable-example\n"
        "description: Use when checking that the portable catalog installer "
        "copies a pinned skill.\n"
        "---\n\n"
        "# Portable example\n",
        encoding="utf-8",
    )
    (second_bundle / "SKILL.md").write_text(
        "---\n"
        "name: portable-second\n"
        "description: Use when checking that an existing provenance lock updates cleanly.\n"
        "---\n\n"
        "# Portable second\n",
        encoding="utf-8",
    )
    _git("init", "-q", str(repository))
    _git("-C", str(repository), "config", "user.name", "Fixture")
    _git("-C", str(repository), "config", "user.email", "fixture@example.invalid")
    _git("-C", str(repository), "add", ".")
    _git("-C", str(repository), "commit", "-q", "-m", "fixture")
    commit = _git("-C", str(repository), "rev-parse", "HEAD", capture=True).strip()
    entry = {
        "id": "fixture/source/portable-example",
        "name": "portable-example",
        "source": {
            "repository": repository.resolve().as_uri(),
            "commit": commit,
            "path": "skills/portable-example",
        },
    }
    second_entry = {
        **entry,
        "id": "fixture/source/portable-second",
        "name": "portable-second",
        "source": {**entry["source"], "path": "skills/portable-second"},
    }
    target = tmp_path / "project" / ".agents" / "skills"

    destination = catalog.install_entry(entry, target, dry_run=False)
    catalog.install_entry(second_entry, target, dry_run=False)

    assert (destination / "SKILL.md").is_file()
    lock = json.loads((target / ".deepseek-skills.lock.json").read_text(encoding="utf-8"))
    assert lock["skills"][entry["id"]]["commit"] == commit
    assert lock["skills"][second_entry["id"]]["commit"] == commit
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        catalog.install_entry(entry, target, dry_run=False)


def _git(*args: str, capture: bool = False) -> str:
    process = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=capture,
        text=True,
    )
    return process.stdout or ""

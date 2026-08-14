from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from deepseek_skill_doctor import __version__ as doctor_version
from deepseek_skill_doctor.checker import check_path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "catalog" / "skills"
REPORTS_DIR = ROOT / "reports"
SCHEMA_PATH = ROOT / "catalog" / "schema.json"
CATALOG_MD = ROOT / "CATALOG.md"
DOCTOR_COMMIT = "fcd0ee835367a02944654c3de2970758dd676811"
SKILLS_REF_COMMIT = "69ef37e9424c0a7ea9dd2293b559e43ec8176379"
SKILL_VALIDATOR_VERSION = "1.6.0"

CATEGORY_NAMES = {
    "deepseek": "DeepSeek tooling",
    "development": "Development",
    "design": "Design",
    "productivity": "Productivity",
    "security": "Security",
}


def load_entries() -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CATALOG_DIR.glob("*.json"))
    ]


def report_path(entry: dict[str, Any]) -> Path:
    return REPORTS_DIR / f"{entry['id'].replace('/', '--').lower()}.json"


def check_catalog(*, require_reports: bool = True) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors: list[str] = []
    entries = load_entries()
    seen_ids: set[str] = set()

    for entry_file, entry in zip(sorted(CATALOG_DIR.glob("*.json")), entries, strict=True):
        for issue in sorted(validator.iter_errors(entry), key=lambda item: list(item.path)):
            location = ".".join(str(part) for part in issue.path) or "<root>"
            errors.append(f"{entry_file.name}: {location}: {issue.message}")
        entry_id = entry.get("id")
        if isinstance(entry_id, str):
            if entry_id in seen_ids:
                errors.append(f"duplicate id: {entry_id}")
            seen_ids.add(entry_id)
        if not require_reports:
            continue
        expected_report = report_path(entry)
        if not expected_report.is_file():
            errors.append(f"missing report: {expected_report.relative_to(ROOT)}")
            continue
        report = json.loads(expected_report.read_text(encoding="utf-8"))
        if report.get("id") != entry_id:
            errors.append(f"{expected_report.name}: id does not match entry")
        if report.get("source") != entry.get("source"):
            errors.append(f"{expected_report.name}: source does not match entry")
        for result_name in ("agent_skills_spec", "dsh_profile", "skill_validator_structure"):
            if report.get("results", {}).get(result_name, {}).get("errors"):
                errors.append(f"{expected_report.name}: {result_name} has errors")
    return errors


def render_catalog(entries: list[dict[str, Any]]) -> str:
    reports = {
        entry["id"]: json.loads(report_path(entry).read_text(encoding="utf-8")) for entry in entries
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["category"]].append(entry)

    lines = [
        "# Catalog",
        "",
        (
            "Every source link below is pinned to the commit that was checked. `pass` means no "
            "error; warnings remain visible and are not silently promoted to a clean result."
        ),
        "",
    ]
    for category in CATEGORY_NAMES:
        items = sorted(grouped.get(category, []), key=lambda item: item["name"])
        if not items:
            continue
        lines.extend(
            [
                f"## {CATEGORY_NAMES[category]}",
                "",
                "| Skill | What it does | Static report | Risk hints | License |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for entry in items:
            report = reports[entry["id"]]
            source = entry["source"]
            source_url = f"{source['repository']}/tree/{source['commit']}/{source['path']}"
            report_url = report_path(entry).relative_to(ROOT).as_posix()
            generic = report["results"]["skill_validator_structure"]
            dsh = report["results"]["dsh_profile"]
            warning_count = generic["warnings"] + dsh["warnings"]
            status = "pass" if warning_count == 0 else f"pass · {warning_count} warning(s)"
            risk = entry["risk"]
            risk_text = (
                f"network: {risk['network']}; commands: {'yes' if risk['commands'] else 'no'}; "
                f"writes: {risk['writes']}"
            )
            lines.append(
                f"| [`{entry['name']}`]({source_url}) | {entry['description']} | "
                f"[{status}]({report_url}) | {risk_text} | {entry['license']['spdx']} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def verify_entries(
    entries: list[dict[str, Any]],
    *,
    skill_validator: Path,
    verified_at: str,
) -> dict[str, dict[str, Any]]:
    repositories: dict[tuple[str, str], list[str]] = defaultdict(list)
    for entry in entries:
        source = entry["source"]
        repositories[(source["repository"], source["commit"])].append(source["path"])

    reports: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="awesome-deepseek-skills-") as temp_dir:
        temp_root = Path(temp_dir)
        checkouts: dict[tuple[str, str], Path] = {}
        for index, ((repository, commit), paths) in enumerate(sorted(repositories.items())):
            checkout = temp_root / f"repo-{index}"
            _checkout(repository, commit, paths, checkout)
            checkouts[(repository, commit)] = checkout

        for entry in entries:
            source = entry["source"]
            checkout = checkouts[(source["repository"], source["commit"])]
            bundle = _safe_source_path(checkout, source["path"])
            reports[entry["id"]] = _verify_bundle(
                entry,
                bundle,
                skill_validator=skill_validator,
                verified_at=verified_at,
            )
    return reports


def _verify_bundle(
    entry: dict[str, Any],
    bundle: Path,
    *,
    skill_validator: Path,
    verified_at: str,
) -> dict[str, Any]:
    doctor_report = check_path(bundle)
    spec_findings = [
        item for item in doctor_report.findings if item.code == "AGENT_SKILLS_SPEC_INVALID"
    ]
    dsh_findings = [
        item for item in doctor_report.findings if item.code != "AGENT_SKILLS_SPEC_INVALID"
    ]

    process = subprocess.run(
        [
            str(skill_validator),
            "validate",
            "structure",
            "-o",
            "json",
            "--allow-dirs=agents",
            str(bundle),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if process.returncode not in {0, 1, 2}:
        raise RuntimeError(f"skill-validator failed for {entry['id']}: {process.stderr.strip()}")
    structure = json.loads(process.stdout)
    structure_findings = [
        {
            "level": item["level"],
            "category": item["category"],
            "message": item["message"],
            **({"file": item["file"]} if item.get("file") else {}),
        }
        for item in structure.get("results", [])
        if item.get("level") in {"error", "warning"}
    ]

    return {
        "schema_version": 1,
        "id": entry["id"],
        "verified_at": verified_at,
        "source": entry["source"],
        "tools": {
            "agent_skills_reference_commit": SKILLS_REF_COMMIT,
            "deepseek_skill_doctor": {"version": doctor_version, "commit": DOCTOR_COMMIT},
            "skill_validator": SKILL_VALIDATOR_VERSION,
        },
        "results": {
            "agent_skills_spec": {
                "status": _status(len(spec_findings), 0),
                "errors": len(spec_findings),
                "warnings": 0,
            },
            "dsh_profile": {
                "status": _status(
                    sum(item.severity == "error" for item in dsh_findings),
                    sum(item.severity == "warning" for item in dsh_findings),
                ),
                "errors": sum(item.severity == "error" for item in dsh_findings),
                "warnings": sum(item.severity == "warning" for item in dsh_findings),
                "findings": [
                    item.to_dict() | {"path": _relative_finding_path(item.path, bundle)}
                    for item in dsh_findings
                ],
            },
            "skill_validator_structure": {
                "status": _status(structure.get("errors", 0), structure.get("warnings", 0)),
                "errors": structure.get("errors", 0),
                "warnings": structure.get("warnings", 0),
                "tokens": structure.get("token_counts", {}).get("total", 0),
                "findings": structure_findings,
            },
        },
    }


def install_entry(entry: dict[str, Any], target: Path, *, dry_run: bool) -> Path:
    target = target.resolve()
    destination = target / entry["name"]
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite {destination}")
    if dry_run:
        return destination

    source = entry["source"]
    with tempfile.TemporaryDirectory(prefix="deepseek-skill-install-") as temp_dir:
        checkout = Path(temp_dir) / "repo"
        _checkout(source["repository"], source["commit"], [source["path"]], checkout)
        bundle = _safe_source_path(checkout, source["path"])
        if any(path.is_symlink() for path in bundle.rglob("*")):
            raise RuntimeError("refusing to install a bundle containing symbolic links")
        report = check_path(bundle)
        if report.count("error"):
            codes = ", ".join(item.code for item in report.findings if item.severity == "error")
            raise RuntimeError(f"source no longer passes the pinned DSH profile: {codes}")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle, destination)

    lock_path = target / ".deepseek-skills.lock.json"
    lock = {"schema_version": 1, "skills": {}}
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock.setdefault("skills", {})[entry["id"]] = {
        "name": entry["name"],
        "repository": source["repository"],
        "commit": source["commit"],
        "path": source["path"],
    }
    temporary_lock = lock_path.with_suffix(".tmp")
    temporary_lock.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_lock.replace(lock_path)
    return destination


def _checkout(repository: str, commit: str, paths: list[str], destination: Path) -> None:
    empty_hooks = destination.parent / ".empty-git-hooks"
    empty_hooks.mkdir(exist_ok=True)
    _run(["git", "init", "-q", str(destination)])
    _run(
        ["git", "-C", str(destination), "remote", "add", "origin", _repository_remote(repository)]
    )
    _run(["git", "-C", str(destination), "sparse-checkout", "init", "--cone"])
    _run(["git", "-C", str(destination), "sparse-checkout", "set", *sorted(set(paths))])
    _run(
        [
            "git",
            "-C",
            str(destination),
            "-c",
            f"core.hooksPath={empty_hooks.as_posix()}",
            "fetch",
            "--depth=1",
            "--filter=blob:none",
            "origin",
            commit,
        ],
        timeout=180,
    )
    _run(
        [
            "git",
            "-C",
            str(destination),
            "-c",
            f"core.hooksPath={empty_hooks.as_posix()}",
            "checkout",
            "--detach",
            "FETCH_HEAD",
        ]
    )
    actual = _run(["git", "-C", str(destination), "rev-parse", "HEAD"], capture=True).strip()
    if actual != commit:
        raise RuntimeError(f"expected {commit}, checked out {actual}")


def _repository_remote(repository: str) -> str:
    if re.fullmatch(r"https://github\.com/[^/]+/[^/]+", repository):
        return f"{repository}.git"
    return repository


def _run(command: list[str], *, timeout: int = 60, capture: bool = False) -> str:
    process = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return process.stdout or ""


def _safe_source_path(checkout: Path, relative: str) -> Path:
    path = (checkout / relative).resolve()
    path.relative_to(checkout.resolve())
    if not (path / "SKILL.md").is_file():
        raise FileNotFoundError(f"missing SKILL.md at {relative}")
    return path


def _relative_finding_path(path: str | None, bundle: Path) -> str | None:
    if path is None:
        return None
    file_part, separator, line = path.rpartition(":")
    candidate = Path(file_part if separator and line.isdigit() else path)
    try:
        relative = candidate.resolve().relative_to(bundle.resolve()).as_posix()
    except (OSError, ValueError):
        return path
    return f"{relative}:{line}" if separator and line.isdigit() else relative


def _status(errors: int, warnings: int) -> str:
    if errors:
        return "error"
    return "warnings" if warnings else "pass"


def _find_entry(entries: list[dict[str, Any]], entry_id: str) -> dict[str, Any]:
    for entry in entries:
        if entry["id"].lower() == entry_id.lower():
            return entry
    raise KeyError(f"unknown skill id: {entry_id}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and install the pinned skill catalog")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="validate catalog entries and committed reports")
    subparsers.add_parser("list", help="list catalog entries")

    render = subparsers.add_parser("render", help="render CATALOG.md")
    render.add_argument("--write", action="store_true")
    render.add_argument("--check", action="store_true")

    verify = subparsers.add_parser("verify", help="fetch pinned sources and reproduce reports")
    verify.add_argument("--skill-validator", type=Path, required=True)
    verify.add_argument("--verified-at", required=True)
    verify.add_argument("--write", action="store_true")
    verify.add_argument("--check", action="store_true")

    install = subparsers.add_parser("install", help="install one pinned entry")
    install.add_argument("id")
    install.add_argument("--target", type=Path, default=Path(".agents/skills"))
    install.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    entries = load_entries()
    if args.command == "check":
        errors = check_catalog()
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print(f"Catalog is valid: {len(entries)} entries")
        return 0
    if args.command == "list":
        for entry in entries:
            print(f"{entry['id']}\t{entry['category']}\t{entry['description']}")
        return 0
    if args.command == "render":
        output = render_catalog(entries)
        if args.check:
            if not CATALOG_MD.exists() or CATALOG_MD.read_text(encoding="utf-8") != output:
                print("CATALOG.md is out of date", file=sys.stderr)
                return 1
        elif args.write:
            CATALOG_MD.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    if args.command == "verify":
        errors = check_catalog(require_reports=False)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        generated = verify_entries(
            entries,
            skill_validator=args.skill_validator.resolve(),
            verified_at=args.verified_at,
        )
        for entry in entries:
            path = report_path(entry)
            text = json.dumps(generated[entry["id"]], indent=2, sort_keys=True) + "\n"
            if args.check:
                if not path.exists() or path.read_text(encoding="utf-8") != text:
                    print(f"report is out of date: {path.relative_to(ROOT)}", file=sys.stderr)
                    return 1
            elif args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            else:
                print(text, end="")
        return 0
    if args.command == "install":
        try:
            entry = _find_entry(entries, args.id)
            destination = install_entry(entry, args.target, dry_run=args.dry_run)
        except (FileExistsError, FileNotFoundError, KeyError, RuntimeError) as exc:
            print(f"deepseek-skills: {exc}", file=sys.stderr)
            return 1
        action = "Would install" if args.dry_run else "Installed"
        print(f"{action} {entry['id']} at {destination}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

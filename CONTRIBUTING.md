# Contributing

Add one JSON file under `catalog/skills/`. Do not copy third-party skill contents into this repository.

A submission needs:

- a public GitHub repository and an immutable 40-character commit;
- a direct path to one `<name>/SKILL.md` bundle;
- license evidence at that commit;
- a description that says what the skill does and when DSH should load it;
- honest network, command, and write hints;
- no errors from the pinned Agent Skills, DSH, or structure checks.

Warnings are allowed when they are understood and remain visible. Keep descriptions factual; do not add star counts, “best” claims, or generated testimonials.

Run:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run pytest
uv run python scripts/catalog.py check
uv run python scripts/catalog.py render --check
```

Maintainers regenerate the remote-source report before merging. If a skill executes downloaded code, accesses credentials, or changes external state, call that out in `risk` and `notes`.


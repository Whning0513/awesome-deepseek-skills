# Awesome DeepSeek Skills

[中文](README.zh-CN.md)

A small, pinned catalog of Agent Skills that can be loaded by DeepSeek Harness (DSH). Every entry has an immutable source commit, a license pointer, a static report, and basic network/command/write hints.

This is deliberately not a scrape of every repository containing `SKILL.md`. The first catalog is small enough to reproduce in CI.

## Browse

See [the generated catalog](CATALOG.md), or list the machine-readable entries:

```bash
uv sync --locked
uv run python scripts/catalog.py list
```

The initial set includes DeepSeek protocol diagnostics and a few established design and development skills from Anthropic, Superpowers, and Trail of Bits.

## Install one pinned skill

The installer checks out the exact commit in the entry, refuses to overwrite an existing directory, rejects symlinked files, and runs the DSH profile before copying anything. It does not execute skill scripts.

```bash
uv run python scripts/catalog.py install \
  obra/superpowers/verification-before-completion \
  --target /path/to/project/.agents/skills
```

DSH discovers direct children of `.agents/skills` and `.dsh/skills`. The installer records provenance in `.deepseek-skills.lock.json` next to the installed bundles.

## What “verified” means here

Each pinned source is checked with:

- the Agent Skills reference parser used by [`deepseek-skill-doctor`](https://github.com/Whning0513/deepseek-skill-doctor);
- [`skill-validator v1.6.0`](https://github.com/agent-ecosystem/skill-validator/releases/tag/v1.6.0), structure mode only;
- the DeepSeek/DSH compatibility profile.

Structure mode is intentional: external link checks depend on live websites and are not reproducible. Warnings stay in the report and the catalog table. No model is used as a judge.

This is not a security audit. A skill can contain unsafe instructions or scripts even when its format is valid. Read the source, the risk hints, and the license before installing it.

## Reproduce the reports

CI downloads the pinned upstream validator binary and verifies its published SHA-256. Locally, pass the same binary path:

```bash
uv run python scripts/catalog.py verify \
  --skill-validator /path/to/skill-validator \
  --verified-at 2026-08-14 \
  --check
```

## Add a skill

See [CONTRIBUTING.md](CONTRIBUTING.md). A submission needs a public source, immutable commit, license evidence, a useful DSH trigger in `description`, and a reproduced report. New projects are welcome, but they stay marked `new`; age and popularity are not invented by the catalog.

MIT licensed. Catalog entries retain their own licenses. This is a community project, not an official DeepSeek component.


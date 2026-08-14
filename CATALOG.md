# Catalog

Every source link below is pinned to the commit that was checked. `pass` means no error; warnings remain visible and are not silently promoted to a clean result.

## DeepSeek tooling

| Skill | What it does | Static report | Risk hints | License |
| --- | --- | --- | --- | --- |
| [`deepseek-protocol-doctor`](https://github.com/Whning0513/deepseek-protocol-doctor/tree/7f6e8ddbace09cc59252694002613d5abe5e2d5c/skills/deepseek-protocol-doctor) | Checks DeepSeek request histories, tool loops, reasoning_content handling, and SSE captures offline. | [pass](reports/whning0513--deepseek-protocol-doctor--deepseek-protocol-doctor.json) | network: install-only; commands: yes; writes: none | MIT |
| [`deepseek-skill-doctor`](https://github.com/Whning0513/deepseek-skill-doctor/tree/fcd0ee835367a02944654c3de2970758dd676811/skills/deepseek-skill-doctor) | Checks Agent Skills for DSH discovery, routing, portability, and unsafe DeepSeek protocol advice. | [pass](reports/whning0513--deepseek-skill-doctor--deepseek-skill-doctor.json) | network: install-only; commands: yes; writes: none | MIT |

## Development

| Skill | What it does | Static report | Risk hints | License |
| --- | --- | --- | --- | --- |
| [`gh-cli`](https://github.com/trailofbits/skills/tree/304c81a8cefb6e3c029ebd0d12940ccf0713eccb/plugins/gh-cli/skills/gh-cli) | Uses authenticated GitHub CLI commands for repositories, pull requests, issues, releases, and API access. | [pass · 1 warning(s)](reports/trailofbits--skills--gh-cli.json) | network: required; commands: yes; writes: external | CC-BY-SA-4.0 |
| [`systematic-debugging`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging) | Uses reproducible evidence, data-flow tracing, and single-hypothesis tests before proposing a bug fix. | [pass · 10 warning(s)](reports/obra--superpowers--systematic-debugging.json) | network: optional; commands: yes; writes: workspace | MIT |
| [`test-driven-development`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/test-driven-development) | Runs a red-green-refactor workflow and requires observing a meaningful failing test before implementation. | [pass · 1 warning(s)](reports/obra--superpowers--test-driven-development.json) | network: optional; commands: yes; writes: workspace | MIT |
| [`verification-before-completion`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/verification-before-completion) | Requires fresh command output and direct evidence before claiming that work is complete, fixed, or passing. | [pass](reports/obra--superpowers--verification-before-completion.json) | network: optional; commands: yes; writes: none | MIT |
| [`writing-plans`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-plans) | Turns an approved design into small implementation tasks with exact files, commands, tests, and commit boundaries. | [pass · 1 warning(s)](reports/obra--superpowers--writing-plans.json) | network: none; commands: no; writes: workspace | MIT |

## Design

| Skill | What it does | Static report | Risk hints | License |
| --- | --- | --- | --- | --- |
| [`frontend-design`](https://github.com/anthropics/skills/tree/f6656c1256d5a8adfa37db9110046ef20bac644c/skills/frontend-design) | Guides deliberate visual direction, typography, layout, responsive behavior, and interface self-critique. | [pass · 1 warning(s)](reports/anthropics--skills--frontend-design.json) | network: optional; commands: yes; writes: workspace | Apache-2.0 |

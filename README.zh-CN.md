# Awesome DeepSeek Skills

[English](README.md) | 中文

这是一个给 DeepSeek Harness（DSH）用的小型 Agent Skills 目录。每条记录都固定到具体 commit，同时保存许可证位置、静态检查报告，以及是否联网、执行命令、写入文件这些基本提示。

它不是搜到 `SKILL.md` 就全收的爬虫。首批目录故意做得不大，保证 CI 真能逐条复现。

## 看目录

直接看[生成后的目录](CATALOG.md)，或者读取机器数据：

```bash
uv sync --locked
uv run python scripts/catalog.py list
```

首批收了 DeepSeek 协议排查工具，以及 Anthropic、Superpowers、Trail of Bits 里几条相对轻量的设计和开发 Skill。

## 安装固定版本

安装器只检出目录记录里的 commit；遇到同名目录会拒绝覆盖，也会拒绝带符号链接的包。复制前会跑一次 DSH profile，但不会执行 Skill 里的脚本。

```bash
uv run python scripts/catalog.py install \
  obra/superpowers/verification-before-completion \
  --target /path/to/project/.agents/skills
```

DSH 会发现 `.agents/skills` 和 `.dsh/skills` 的直接子目录。安装来源会记录在同级的 `.deepseek-skills.lock.json`。

## 这里的“已验证”是什么意思

每个固定来源会经过三层静态检查：

- Agent Skills 官方参考解析器；
- [`skill-validator v1.6.0`](https://github.com/agent-ecosystem/skill-validator/releases/tag/v1.6.0) 的 structure 模式；
- DeepSeek/DSH 专项 profile。

没有把外链检查算进来，因为网站状态会变，难以复现。warning 不会被吞掉，而是直接显示在报告和目录表格里。也没有拿另一个模型来主观打分。

这仍然不是安全审计。格式通过不代表指令和脚本安全，安装前请看源码、风险提示和许可证。

## 复现报告

CI 会下载固定版本的上游检查器，并核对发布页给出的 SHA-256。本地可以这样跑：

```bash
uv run python scripts/catalog.py verify \
  --skill-validator /path/to/skill-validator \
  --verified-at 2026-08-14 \
  --check
```

## 收录新 Skill

要求见 [CONTRIBUTING.md](CONTRIBUTING.md)：公开来源、固定 commit、许可证证据、能让 DSH 正确路由的 description，以及可复现报告。新项目可以收，但会如实标成 `new`，不会替它编造社区成熟度。

目录代码采用 MIT License，各 Skill 保留自己的许可证。第三方社区项目，不是 DeepSeek 官方组件。


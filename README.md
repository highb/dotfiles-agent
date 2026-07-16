# dotfiles-agent

Agent-oriented dotfiles managed by [chezmoi](https://www.chezmoi.io).

## What this installs

- [caveman-english](https://github.com/highb/caveman-english) — Brandon's fork
  of the caveman Claude Code extension, vendored into `~/.local/share/caveman`
  and wired into `~/.claude` via its hook installer.
- Agent skills under `~/.claude/skills/` — portable [`SKILL.md`](https://docs.claude.com/en/docs/claude-code/skills)
  files (`name` + `description` frontmatter, Markdown body) that load into any
  agent harness supporting the skills format. Currently:
  - `highb-token-waste-audit` — session meta-analysis: find mechanical,
    repeatable token sinks and route each to its cheapest durable home — shared
    team tooling, a shared docs/runbook update, personal dotfiles, or an agent
    CLAUDE.md/skill note.

## Bootstrap

```sh
chezmoi init --apply highb/dotfiles-agent
```

This command:
1. Clones this repo as the chezmoi source directory.
2. Fetches the caveman-english fork into `~/.local/share/caveman`.
3. Runs `install.sh` from that clone, which copies the caveman hooks into
   `~/.claude/hooks` and merges the hook registrations into
   `~/.claude/settings.json`.

Restart Claude Code after applying to activate the hooks.

## Prerequisites

- [chezmoi](https://www.chezmoi.io/install/) (`brew install chezmoi`)
- Node.js ≥ 18 (`brew install node`)
- git

## Update

```sh
chezmoi update
```

Pulls the latest chezmoi source and re-fetches the caveman-english external
if more than 168 hours have passed since the last fetch.

To force a reinstall of the hooks:

```sh
cd ~/.local/share/caveman && bash install.sh --force
```

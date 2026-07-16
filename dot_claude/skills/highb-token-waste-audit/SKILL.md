---
name: highb-token-waste-audit
description: >-
  Meta-analysis of the current session: find where the model burned tokens on
  repetitive, mechanical work that could be pre-scripted or written down once and
  reused. Decide the right home for each candidate — shared team tooling (an agent
  orchestration tool, internal CLI, or service that every teammate benefits from),
  shared team docs (a runbook/wiki update so nobody re-derives it), a script/alias
  in the user's personal dotfiles (individual workflow), or an agent CLAUDE.md /
  skill note (re-derived knowledge). Produces a ranked table of candidates with a
  concrete sketch and estimated savings. Trigger phrases: "where am I burning
  tokens", "what could be scripted", "automation audit", "token waste",
  "meta-analysis of this session", "what should go in the shared tooling / docs /
  my dotfiles".
---

# highb-token-waste-audit

Look back over the session's own transcript, find the token sinks that are
**mechanical and repeatable**, and route each one to the cheapest durable home.
The goal is not "use fewer tokens right now" — it is "never pay for this shape of
work again, for me or for anyone on my team."

## What counts as waste worth scripting

A candidate is work that is all three of:

1. **Repeated** — the same command shape, tool sequence, or knowledge lookup
   happened 2+ times this session (or is obviously a per-session ritual).
2. **Deterministic** — a fixed script would produce the same result; no judgment
   call in the loop. (Reading a log and *deciding* what's wrong is judgment.
   *Fetching and filtering* the log is deterministic.)
3. **Expensive** — it cost real tokens: many tool round-trips, large tool
   results pulled into context, or long re-derivation the model reasoned through.

Work that is one-off, or where each instance needs a genuine decision, is **not**
a candidate — say so and move on. Do not manufacture automation for its own sake.

## Step 1 — extract the token map

Run the bundled `token_map.py` — it sits in this skill's own directory
(`~/.claude/skills/highb-token-waste-audit/` under Claude Code; use the path
this `SKILL.md` was loaded from on any other harness). With no argument it
auto-locates the most-recently-modified transcript for the current working
directory under `~/.claude/projects/<slug>/`; pass a path to target a specific
one:

```bash
skill_dir=~/.claude/skills/highb-token-waste-audit   # or wherever this SKILL.md lives
python3 "$skill_dir/token_map.py"                     # auto-locate this session
python3 "$skill_dir/token_map.py" /path/to/session.jsonl
```

It reports, from one pass over the JSONL:

- **output tokens** — approximate model work this session.
- **tool call frequency** — every tool by count.
- **bash command heads** — repeated heads flagged `<-- repeated`; each is a
  script candidate.
- **context pulled in by tool** — total `tool_result` bytes per tool, i.e. how
  much each tool dragged into the window (the expensive leg of the rubric above).

If it prints "no transcript found" (different harness, or cwd slug mismatch),
fall back to your own in-context memory of the session — you lived it. The
transcript just makes the token accounting exact.

Then read the transcript for **sequences**: the same 3–4 tool calls in the same
order (e.g. `list_endpoints` → `curl local_url` → `service_logs` on failure) is a
higher-value candidate than any single repeated command, because scripting it
collapses the whole loop.

Also look for **knowledge re-derivation**: long stretches where the model reasoned
out something that is stable and knowable (an API shape, a file layout, a login
flow, a deploy sequence). That's a docs/skill/memory candidate, not a script
candidate.

## Step 2 — before proposing, check it doesn't already exist

Two dead ends to rule out first:

- **Shared team tooling already has it.** Before proposing a new command or
  script, look at whatever shared dev tooling the team already runs — the internal
  CLI, the agent orchestration tool, the Makefile/task runner, the scripts
  directory. Most standard dev-loop rituals are already a command someone wrote.
  Grep its command surface first, e.g.:

  ```bash
  # adapt to the team's actual tool; e.g. a Go/Cobra CLI:
  grep -rhoE 'Use:\s*"[a-z][a-z-]*"' <tool-src>/cmd/ | sort -u
  # or a task runner:
  just --list 2>/dev/null; make help 2>/dev/null; npm run 2>/dev/null
  ```

  If the capability exists and the model just didn't use it, the fix is **not** a
  new script — it's a CLAUDE.md / skill / docs note telling future sessions to
  reach for the existing command. Record that instead.

- **Shared docs already cover it.** If the waste was re-derived knowledge, search
  the team's runbook / wiki / docs site before writing it down again — the answer
  may already exist and just wasn't found. A dead link or a stale page *is* the
  finding: the fix is a docs update, not a new script.

- **A personal-dotfiles home already exists.** Personal scripts have a real home:
  most agent-env tooling can wire a user's dotfiles (or chezmoi) repo into every
  environment it creates — e.g. a `dotfiles set --repo <URL>` step. So "put it in
  your dotfiles" is a concrete, supported action, not hand-waving.

## Step 3 — route each candidate to its home

Decide with this tree, in order:

| Signal | Home | Why |
|--------|------|-----|
| Repeated command / tool sequence that hits a **shared service** or is part of the **standard dev loop**; would help **teammates**, not just this user | **Shared team tooling** — a subcommand in the internal CLI / agent orchestration tool, a task-runner target, or a committed script in the shared repo | Org-wide value belongs in versioned, discoverable, shared tooling. Heavier lift: code + PR + review, and possible **multi-surface parity** (see below). |
| Repeated **knowledge lookup** the whole team re-derives (API shape, deploy sequence, service layout, "how do I X") | **Shared team docs** — a runbook / wiki / docs-site update | One authoritative page kills the re-derivation for everyone. Cheaper than tooling; no code, just prose that has to be findable. |
| Personal workflow, per-user paths, editor/git/shell preference; no value to anyone else | **Personal dotfiles repo** (shell fn / alias / chezmoi), wired into agent envs via the tool's dotfiles hook | Light lift, no PR, no review. Idiosyncratic-by-design work should never bloat shared tooling. |
| Re-derived knowledge that only **this agent / this user** hits, not the whole team | **Agent CLAUDE.md note or a skill** | Nothing to run — the fix is to record the fact so no future session re-reasons it. Link `[[related-memory]]` if it fits the memory system. |
| Capability already exists (Step 2) but went unused | **CLAUDE.md / skill / docs pointer** to the existing command or page | The gap is discovery, not tooling. |
| One-off, or each instance needs a judgment call | **Skip** | Say explicitly why it is not automatable. Do not invent a script. |

**Tie-breaker (shared vs. personal):** ask "would a teammate who has never seen my
session want this exact thing?" Yes → shared tooling or shared docs. Only-me →
dotfiles. When genuinely split, prefer the cheap reversible home first (dotfiles,
or a docs paragraph) and promote to shared tooling later if others ask for it.
Under-scripting the shared surface is cheaper to fix than a speculative subcommand
nobody else wanted.

**Multi-surface parity caveat (shared-tooling candidates only).** Some teams hold
a rule that a user-facing feature is not "shipped" until every surface honors it
(HTTP API + CLI + MCP + UI, or whatever the team's surfaces are). A new command
that hits a shared endpoint can pull that whole obligation in. Flag it in the
proposal so the reader sizes the work honestly — a pure client-side convenience
wrapper (no new shared endpoint) does not.

## Step 4 — output

Produce a ranked table, highest estimated savings first. One row per candidate:

| # | What repeated | Cost signal | Home | Sketch | Est. savings |
|---|---------------|-------------|------|--------|--------------|

- **Cost signal** — concrete: "7 `curl` calls + 3 `service_logs`, ~4k tokens of
  results pulled in" beats "expensive."
- **Sketch** — the actual thing to build: the command/verb name and the endpoint
  it wraps, the docs page + section to add, or the exact shell function for
  dotfiles. Keep it small and buildable, not a spec.
- **Est. savings** — per future session: round-trips removed and/or tokens of
  context avoided. Approximate is fine; show the arithmetic.

Close with a **one-line recommendation** on what to do first — usually the single
highest-savings, lowest-effort candidate (a dotfiles alias, a docs paragraph, or a
CLAUDE.md note), not the ambitious shared-tooling subcommand. If nothing clears the
bar — repeated + deterministic + expensive — say the session was already tight
and name the closest near-miss.

## Guardrails

- Never propose scripting anything that embeds a secret, token, or credential —
  those belong in the secret mechanisms, not a dotfiles alias or committed script.
- Don't propose a shared command that duplicates an existing one, or a docs page
  that already exists (Step 2).
- Don't count the model's *reasoning about the actual task* as waste — only the
  mechanical scaffolding around it.
- Report honestly: if the biggest sink was irreducible task work, say so rather
  than inventing marginal automation to fill the table.

## Maintaining this skill

`token_map.py`'s parsing lives in pure functions (`analyze`, `project_slug`,
`locate_transcript`); `test_token_map.py` covers them with stdlib `unittest`
(no pip install). If you change the transcript schema assumptions or the slug
scheme, run the suite from this directory:

```bash
python3 test_token_map.py            # or: python3 -m unittest -v
```

#!/usr/bin/env python3
"""Token map for the current (or given) Claude Code session transcript.

Ranks tool calls by frequency, bash command heads by repetition (a repeated
head is a script candidate), and tool_results by the context they dragged into
the model's window. Part of the highb-token-waste-audit skill — see SKILL.md.

Usage:
    token_map.py [TRANSCRIPT.jsonl]

With no argument, auto-locates the most-recently-modified transcript for the
current working directory under ~/.claude/projects/<slug>/. Exits non-zero with
a hint if none is found (different harness, or cwd slug mismatch) — fall back to
your own in-context memory of the session.
"""
import json
import os
import re
import sys
from collections import Counter


def locate_transcript() -> str | None:
    # Claude Code slugifies the project path by replacing every non-alphanumeric
    # run with '-', so /Users/x/github.com/y -> -Users-x-github-com-y. A naive
    # '/'->'-' replace misses the dot in "github.com".
    slug = re.sub(r"[^a-zA-Z0-9]", "-", os.getcwd())
    proj = os.path.expanduser(f"~/.claude/projects/{slug}")
    if not os.path.isdir(proj):
        return None
    logs = [os.path.join(proj, f) for f in os.listdir(proj) if f.endswith(".jsonl")]
    if not logs:
        return None
    return max(logs, key=os.path.getmtime)


def human(n: int) -> str:
    for unit in ("", "k", "M"):
        if abs(n) < 1000:
            return f"{n}{unit}"
        n //= 1000
    return f"{n}G"


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else locate_transcript()
    if not path:
        print(
            "no transcript found for this cwd under ~/.claude/projects/ — "
            "fall back to in-context session memory.",
            file=sys.stderr,
        )
        return 1
    if not os.path.isfile(path):
        print(f"transcript not found: {path}", file=sys.stderr)
        return 1

    tool_calls = Counter()
    bash_cmds = Counter()
    result_bytes = Counter()  # tool name -> total bytes of results it pulled in
    out_tokens = 0

    # tool_use id -> tool name, so tool_result rows can be attributed back
    id_to_tool: dict[str, str] = {}

    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = r.get("message")
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            content = m.get("content")

            if role == "assistant":
                out_tokens += (m.get("usage") or {}).get("output_tokens", 0)
                if isinstance(content, list):
                    for b in content:
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        name = b.get("name", "?")
                        tool_calls[name] += 1
                        id_to_tool[b.get("id", "")] = name
                        if name == "Bash":
                            cmd = (b.get("input") or {}).get("command", "").strip()
                            head = cmd.split()[0] if cmd else ""
                            if head:
                                bash_cmds[head] += 1

            # tool_result blocks land on user rows, keyed by tool_use_id
            if isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict) or b.get("type") != "tool_result":
                        continue
                    name = id_to_tool.get(b.get("tool_use_id", ""), "?")
                    result_bytes[name] += len(json.dumps(b.get("content", "")))

    print(f"output tokens (approx model work): {out_tokens}")

    print("\ntool call frequency:")
    for name, n in tool_calls.most_common():
        print(f"  {n:3}  {name}")

    print("\nbash command heads (repetition = script candidate):")
    for cmd, n in bash_cmds.most_common(15):
        flag = "  <-- repeated" if n > 1 else ""
        print(f"  {n:3}  {cmd}{flag}")

    print("\ncontext pulled in by tool (result bytes = tokens dragged in):")
    for name, b in result_bytes.most_common(10):
        print(f"  {human(b):>6}  {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

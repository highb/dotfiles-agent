#!/usr/bin/env python3
"""Tests for token_map.py (highb-token-waste-audit skill).

Stdlib unittest only — no pip install, so it runs anywhere the skill lands.

    python3 test_token_map.py            # or: python3 -m unittest -v

Loads the sibling script by path so it works both in the chezmoi source tree
(where the file is named executable_token_map.py) and at the installed location
(~/.claude/skills/.../token_map.py).
"""
import importlib.util
import json
import os
import tempfile
import unittest


def _load_module():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("token_map.py", "executable_token_map.py"):
        cand = os.path.join(here, name)
        if os.path.isfile(cand):
            spec = importlib.util.spec_from_file_location("token_map", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError("token_map.py not found next to the test")


tm = _load_module()


def assistant(*blocks, out_tokens=0):
    return {"message": {"role": "assistant", "content": list(blocks),
                        "usage": {"output_tokens": out_tokens}}}


def tool_use(name, id="", **inp):
    return {"type": "tool_use", "name": name, "id": id, "input": inp}


def user_result(tool_use_id, content):
    return {"message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}]}}


class ProjectSlug(unittest.TestCase):
    def test_dot_in_path_becomes_dash(self):
        # The bug the old '/'->'-' snippet had: github.com must slug to github-com.
        self.assertEqual(
            tm.project_slug("/Users/x/src/github.com/y/dotfiles-agent"),
            "-Users-x-src-github-com-y-dotfiles-agent",
        )

    def test_leading_slash_becomes_leading_dash(self):
        self.assertTrue(tm.project_slug("/a/b").startswith("-"))


class Analyze(unittest.TestCase):
    def test_tool_frequency_and_output_tokens(self):
        rows = [
            assistant(tool_use("Bash", "1", command="git status"), out_tokens=10),
            assistant(tool_use("Read", "2"), tool_use("Bash", "3", command="git log"),
                      out_tokens=5),
        ]
        m = tm.analyze(rows)
        self.assertEqual(m["out_tokens"], 15)
        self.assertEqual(m["tool_calls"]["Bash"], 2)
        self.assertEqual(m["tool_calls"]["Read"], 1)

    def test_bash_heads_count_first_word_only(self):
        rows = [
            assistant(tool_use("Bash", command="git status")),
            assistant(tool_use("Bash", command="git log --oneline")),
            assistant(tool_use("Bash", command="ls -la")),
        ]
        m = tm.analyze(rows)
        self.assertEqual(m["bash_cmds"]["git"], 2)  # the repeated -> script candidate
        self.assertEqual(m["bash_cmds"]["ls"], 1)

    def test_empty_bash_command_produces_no_head(self):
        m = tm.analyze([assistant(tool_use("Bash", command="   "))])
        self.assertEqual(sum(m["bash_cmds"].values()), 0)

    def test_result_bytes_attributed_to_originating_tool(self):
        rows = [
            assistant(tool_use("Read", "abc")),
            user_result("abc", "x" * 100),
        ]
        m = tm.analyze(rows)
        # json.dumps("xxx...") = 100 chars + 2 quotes
        self.assertEqual(m["result_bytes"]["Read"], 102)

    def test_orphan_result_attributed_to_unknown(self):
        m = tm.analyze([user_result("no-such-id", "hi")])
        self.assertEqual(m["result_bytes"]["?"], len(json.dumps("hi")))

    def test_malformed_rows_are_ignored(self):
        rows = [{"message": None}, {"no_message": 1}, {"message": {"role": "system"}}]
        m = tm.analyze(rows)
        self.assertEqual(m["out_tokens"], 0)
        self.assertEqual(sum(m["tool_calls"].values()), 0)


class ReadRows(unittest.TestCase):
    def test_skips_blank_and_invalid_json_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write('{"a": 1}\n\n   \nnot json\n{"b": 2}\n')
            path = f.name
        self.addCleanup(os.unlink, path)
        rows = list(tm.read_rows(path))
        self.assertEqual(rows, [{"a": 1}, {"b": 2}])


class LocateTranscript(unittest.TestCase):
    def test_returns_newest_jsonl_for_slugged_cwd(self):
        with tempfile.TemporaryDirectory() as home:
            cwd = "/Users/x/github.com/proj"
            proj = os.path.join(home, ".claude", "projects", tm.project_slug(cwd))
            os.makedirs(proj)
            old = os.path.join(proj, "old.jsonl")
            new = os.path.join(proj, "new.jsonl")
            for p in (old, new):
                open(p, "w").close()
            os.utime(old, (1000, 1000))
            os.utime(new, (2000, 2000))
            self.assertEqual(tm.locate_transcript(cwd=cwd, home=home), new)

    def test_none_when_project_dir_missing(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertIsNone(tm.locate_transcript(cwd="/nope", home=home))


class MainAndRender(unittest.TestCase):
    def test_main_ok_on_real_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            json.dump({"message": {"role": "assistant",
                       "content": [tool_use("Bash", command="git s")],
                       "usage": {"output_tokens": 3}}}, f)
            f.write("\n")
            path = f.name
        self.addCleanup(os.unlink, path)
        self.assertEqual(tm.main([path]), 0)

    def test_main_errors_on_missing_file(self):
        self.assertEqual(tm.main(["/does/not/exist.jsonl"]), 1)

    def test_render_flags_repeated_bash_head(self):
        m = tm.analyze([assistant(tool_use("Bash", command="git a")),
                        assistant(tool_use("Bash", command="git b"))])
        out = tm.render(m)
        self.assertIn("<-- repeated", out)
        self.assertIn("tool call frequency", out)


if __name__ == "__main__":
    unittest.main()

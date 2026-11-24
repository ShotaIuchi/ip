"""Checks on the skill documents for the `--with` option (AC-1, AC-9).

SKILL.md files are instructions for an AI, so these tests cannot run the skills. They confirm
that the commands that start another AI carry the agreed permission options, `IP_PEER=1`, the
15-minute limit and the exit-code record,
and that nothing from the dropped `peer.py` / `--implementer` design is left in the repository.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = (ROOT / "plugins" / "review" / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")

# The commands exactly as the spec's "決めた方針" fixes them.
TIME_LIMIT = "perl -e 'alarm 900; exec @ARGV' --"
EXIT_CODE = "; echo \"exit=$?\" >> '<ログのファイル>'"
CODEX_COMMAND = (
    f"IP_PEER=1 {TIME_LIMIT} codex exec --sandbox read-only --ephemeral --skip-git-repo-check --ignore-user-config "
    "--ignore-rules --disable hooks -c web_search=\"disabled\" -C '<リポジトリ>' -o '<結果のファイル>' "
    "- < '<指示のファイル>' > /dev/null 2> '<ログのファイル>'" + EXIT_CODE
)
CLAUDE_COMMAND = (
    f"( cd '<リポジトリ>' && IP_PEER=1 {TIME_LIMIT} claude -p --permission-mode plan --setting-sources \"\" "
    "--strict-mcp-config --tools Bash,Read,Glob,Grep --disallowedTools WebFetch WebSearch "
    "--settings '<サンドボックスの設定>' ) < '<指示のファイル>' > '<結果のファイル>' 2> '<ログのファイル>'" + EXIT_CODE
)
SANDBOX_SETTINGS = {
    "sandbox": {
        "enabled": True,
        "failIfUnavailable": True,
        "allowUnsandboxedCommands": False,
        "autoAllowBashIfSandboxed": False,
        "network": {"strictAllowlist": True},
    }
}


def command_lines(text: str, program: str) -> list[str]:
    """Lines inside fenced code blocks that run `program` (after `( cd … &&`, variables and the time limit)."""
    lines = []
    for block in re.findall(r"```[^\n]*\n(.*?)```", text, re.S):
        for line in block.splitlines():
            try:
                words = shlex.split(line)
            except ValueError:
                continue
            if program in words[: words.index("--") + 2 if "--" in words else 3]:
                lines.append(line.strip())
    return lines


def run_words(line: str) -> list[str]:
    """Shell words of the command that starts the AI: inside `( cd … && … )` if any, before the redirections."""
    words = shlex.split(line.split("; echo ")[0])
    if words[0] == "(":
        words = words[words.index("&&") + 1:words.index(")")]
    return words


class ReviewCommandTest(unittest.TestCase):
    def test_codex_command_is_written_as_decided(self):
        self.assertEqual(command_lines(REVIEW, "codex"), [CODEX_COMMAND])

    def test_claude_command_is_written_as_decided(self):
        self.assertEqual(command_lines(REVIEW, "claude"), [CLAUDE_COMMAND])

    def test_permission_options_and_ip_peer_are_present(self):
        [codex_line] = command_lines(REVIEW, "codex")
        [claude_line] = command_lines(REVIEW, "claude")
        codex = run_words(codex_line)
        claude = run_words(claude_line)
        for words, program, required in (
            (codex, "codex", ["exec", "--sandbox", "read-only", "--ephemeral", "--ignore-user-config",
                              "--ignore-rules", "--disable", "hooks", "-c", "web_search=disabled"]),
            (claude, "claude", ["-p", "--permission-mode", "plan", "--setting-sources", "", "--strict-mcp-config",
                                "--tools", "Bash,Read,Glob,Grep", "--disallowedTools", "WebFetch", "WebSearch",
                                "--settings"]),
        ):
            # IP_PEER=1, then the 15-minute limit, then the AI itself.
            self.assertEqual(words[:6], ["IP_PEER=1", "perl", "-e", "alarm 900; exec @ARGV", "--", program])
            for word in required:
                with self.subTest(command=program, word=word):
                    self.assertIn(word, words)

    def test_claude_runs_in_the_repository_and_both_record_the_exit_code(self):
        [codex_line] = command_lines(REVIEW, "codex")
        [claude_line] = command_lines(REVIEW, "claude")
        # `cd` comes first inside a subshell, and the redirections sit outside it so a failed `cd` reaches the log.
        claude = shlex.split(claude_line.split("; echo ")[0])
        self.assertEqual(claude[:4], ["(", "cd", "<リポジトリ>", "&&"])
        self.assertEqual(claude[claude.index(")"):claude.index(")") + 7],
                         [")", "<", "<指示のファイル>", ">", "<結果のファイル>", "2>", "<ログのファイル>"])
        # Codex writes its result with -o, so its standard output is thrown away.
        codex = shlex.split(codex_line.split("; echo ")[0])
        self.assertEqual(codex[codex.index("-") + 1:codex.index("-") + 7],
                         ["<", "<指示のファイル>", ">", "/dev/null", "2>", "<ログのファイル>"])
        for line in (codex_line, claude_line):
            with self.subTest(line=line[:40]):
                self.assertEqual(shlex.split(line)[-4:], ["echo", "exit=$?", ">>", "<ログのファイル>"])

    def test_paths_are_single_quoted(self):
        for line in command_lines(REVIEW, "codex") + command_lines(REVIEW, "claude"):
            for placeholder in re.findall(r"<[^<>]+>", line):
                with self.subTest(placeholder=placeholder):
                    self.assertNotRegex(line, rf"(?<!')({re.escape(placeholder)})|({re.escape(placeholder)})(?!')")

    def test_sandbox_settings_close_the_network(self):
        found = [json.loads(m) for m in re.findall(r'^\s*(\{"sandbox".*\})\s*$', REVIEW, re.M)]
        self.assertEqual(found, [SANDBOX_SETTINGS])
        self.assertNotIn("'", json.dumps(SANDBOX_SETTINGS))  # fits inside the single quotes as is

    def test_commands_are_used_as_written(self):
        self.assertIn("`<…>` の部分だけを置き換えて、**そのまま** 使う", REVIEW)


class LeftoverTest(unittest.TestCase):
    def test_no_peer_script_or_implementer_remains(self):  # AC-9
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split("\0")
        this_file = Path(__file__).resolve().relative_to(ROOT).as_posix()
        for name in tracked:
            path = ROOT / name
            if not name or name == this_file or name.startswith("docs/specs/") or not path.is_file():
                continue
            with self.subTest(path=name):
                self.assertNotIn("peer.py", Path(name).name)
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn("peer.py", text)
                self.assertNotIn("--implementer", text)


if __name__ == "__main__":
    unittest.main()

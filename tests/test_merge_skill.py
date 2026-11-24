"""Checks on the git-kit:merge skill document.

SKILL.md is instructions for an AI, so these tests cannot run the skill. They confirm the frontmatter (AC-1), that the
document stays at the level of instructions (AC-7), and that its code blocks never run a command the spec rules out.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MERGE = (ROOT / "plugins" / "git-kit" / "skills" / "merge" / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(text: str) -> str:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if match is None:
        raise AssertionError("SKILL.md has no frontmatter")
    return match.group(1)


def code_lines(text: str) -> list[str]:
    return [line.strip() for block in re.findall(r"```[^\n]*\n(.*?)```", text, re.S) for line in block.splitlines()]


class MergeSkillTest(unittest.TestCase):
    def test_frontmatter(self):  # AC-1
        front = frontmatter(MERGE)
        self.assertRegex(front, r"(?m)^name: merge$")
        self.assertRegex(front, r"(?m)^argument-hint: \S")
        description = re.search(r"(?ms)^description: >\n(.*?)(?=^\S)", front).group(1)
        for phrase in ("「マージして」", "「main を取り込んで」"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, description)

    def test_stays_at_the_level_of_instructions(self):  # AC-7
        self.assertLessEqual(len(MERGE.splitlines()), 250)

    def test_trial_merge_does_not_commit(self):  # AC-4
        self.assertIn("git merge --no-commit --no-ff '<theirs の sha>'", code_lines(MERGE))

    def test_no_code_block_runs_a_ruled_out_command(self):  # やらないこと, 絶対に守ること
        ruled_out = re.compile(r"\bgit\s+(push|pull|rebase|cherry-pick|stash|reset|clean)\b|--no-verify")
        for line in code_lines(MERGE):
            with self.subTest(line=line[:60]):
                self.assertIsNone(ruled_out.search(line))


if __name__ == "__main__":
    unittest.main()

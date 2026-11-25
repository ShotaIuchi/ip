"""Checks on the review:loop skill document (AC-1, AC-4, AC-5).

SKILL.md is instructions for an AI, so these tests cannot run the skill. They confirm the frontmatter, that the
document stays at the level of instructions, and that its code blocks never commit, push or throw work away.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOOP = (ROOT / "plugins" / "review" / "skills" / "loop" / "SKILL.md").read_text(encoding="utf-8")


def code_lines(text: str) -> list[str]:
    return [line.strip() for block in re.findall(r"```[^\n]*\n(.*?)```", text, re.S) for line in block.splitlines()]


class LoopSkillTest(unittest.TestCase):
    def test_frontmatter(self):  # AC-1
        front = re.match(r"---\n(.*?)\n---\n", LOOP, re.S).group(1)
        self.assertRegex(front, r"(?m)^name: loop$")
        self.assertRegex(front, r"(?m)^argument-hint: \S")
        description = re.search(r"(?ms)^description: >\n(.*?)(?=^\S)", front).group(1)
        for phrase in ("「レビューして直して」", "「指摘が無くなるまで直して」"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, description)

    def test_stays_at_the_level_of_instructions(self):  # AC-5
        self.assertLessEqual(len(LOOP.splitlines()), 250)

    def test_no_code_block_commits_pushes_or_discards_work(self):  # AC-4
        ruled_out = re.compile(r"\bgit\s+(commit|push|stash|reset|clean|checkout|restore)\b|--no-verify")
        for line in code_lines(LOOP):
            with self.subTest(line=line[:60]):
                self.assertIsNone(ruled_out.search(line))


if __name__ == "__main__":
    unittest.main()

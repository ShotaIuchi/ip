"""Checks for the quick plugin: hs and hhs share one body and differ only in the model settings."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "plugins" / "quick" / "skills"
EXPECTED = {"hs": ("sonnet", "medium"), "hhs": ("haiku", "low")}


def split(name: str) -> tuple[dict[str, str], str]:
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n\n# [^\n]*\n(.*)", text, re.S)
    assert m, f"{name}: frontmatter or title missing"
    front = dict(line.split(": ", 1) for line in m.group(1).splitlines())
    return front, m.group(2)


class QuickSkillTest(unittest.TestCase):
    def test_model_and_effort(self):
        for name, (model, effort) in EXPECTED.items():
            with self.subTest(skill=name):
                front, _ = split(name)
                self.assertEqual(front["name"], name)
                self.assertEqual(front["model"], model)
                self.assertEqual(front["effort"], effort)
                self.assertEqual(front["disable-model-invocation"], "true")

    def test_bodies_match(self):
        bodies = {name: split(name)[1] for name in EXPECTED}
        self.assertEqual(bodies["hs"], bodies["hhs"], "hs and hhs must keep the same instructions")
        self.assertIn("$ARGUMENTS", bodies["hs"])


if __name__ == "__main__":
    unittest.main()

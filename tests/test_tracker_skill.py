"""Structural checks on the tracker plugin and the dev:decompose move onto it (AC-1 … AC-9).

SKILL.md and the reference files are instructions for an AI, so these tests cannot run the skills, and they do not pin
the wording of the instructions. They confirm the manifests and versions, the frontmatter and the length limits, that
each reference file has a non-empty section for every common verb, that the operating-file format has the agreed
headings, that decompose carries no tool-specific operation, and that no file names a real project or asks for
credentials to be written down.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "plugins" / "tracker"
DEV = ROOT / "plugins" / "dev"
ISSUE_DIR = TRACKER / "skills" / "issue"
SETUP_DIR = TRACKER / "skills" / "setup"

ISSUE = ISSUE_DIR / "SKILL.md"
SETUP = SETUP_DIR / "SKILL.md"
TOOL_REFERENCES = sorted((ISSUE_DIR / "references").glob("*.md"))
FORMAT = SETUP_DIR / "references" / "tracker-format.md"
DECOMPOSE = DEV / "skills" / "decompose" / "SKILL.md"
ALL_DOCS = [ISSUE, SETUP, *TOOL_REFERENCES, FORMAT, DECOMPOSE]

VERBS = ("探す", "見る", "作る", "子を作る", "更新", "状態を進める", "コメント", "依存を付ける", "工数を記録する")
FORMAT_HEADINGS = ("接続先", "状態の流れ", "課題の種類と必須項目", "テンプレート", "ラベルと命名", "工数", "代わりの決まり", "その他")
LINE_LIMITS = {ISSUE: 150, SETUP: 150, FORMAT: 100, DECOMPOSE: 221,
               ISSUE_DIR / "references" / "jira.md": 100, ISSUE_DIR / "references" / "github.md": 100}
# The operations AC-7 names; the ones written in the reference files are added in the test.
DECOMPOSE_FORBIDDEN = {"gh issue create", "addSubIssue", "addBlockedBy", "createJiraIssue", "createJiraIssueLink",
                       "editJiraIssue", "getJiraIssue"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(read(path))


def frontmatter(text: str) -> str:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if match is None:
        raise AssertionError("no frontmatter")
    return match.group(1)


def sections(text: str, level: str) -> dict[str, str]:
    """Heading text -> body for headings of exactly `level`, ignoring lines inside fenced code blocks for headings."""
    result: dict[str, list[str]] = {}
    current: list[str] | None = None
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            match = re.match(rf"{level} (.+)$", line)
            if match:
                current = result.setdefault(match.group(1).strip(), [])
                continue
            if re.match(r"#{1,%d} " % len(level), line):
                current = None
                continue
        if current is not None:
            current.append(line)
    return {head: "\n".join(body) for head, body in result.items()}


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


class ManifestTest(unittest.TestCase):
    def test_tracker_manifests_and_marketplace(self):  # AC-1
        for kind in (".claude-plugin", ".codex-plugin"):
            with self.subTest(kind=kind):
                manifest = load(TRACKER / kind / "plugin.json")
                self.assertEqual(manifest["name"], "tracker")
                self.assertEqual(manifest["version"], "0.1.0")
        sources = {e["name"]: e["source"] for e in load(ROOT / ".claude-plugin" / "marketplace.json")["plugins"]}
        self.assertEqual(sources.get("tracker"), "./plugins/tracker")

    def test_versions_and_readme(self):  # AC-8
        for kind in (".claude-plugin", ".codex-plugin"):
            with self.subTest(kind=kind):
                self.assertEqual(load(DEV / kind / "plugin.json")["version"], "0.4.0")
        readme = read(ROOT / "README.md")
        self.assertRegex(readme, r"(?m)^\| \[dev\]\(plugins/dev\) \| 0\.4\.0 \|")
        self.assertRegex(readme, r"(?m)^\| \[tracker\]\(plugins/tracker\) \| 0\.1\.0 \|")
        for line in ("/plugin install tracker@ip", "codex plugin add tracker@ip", "copilot plugin install tracker@ip",
                     "claude plugin update tracker@ip"):
            with self.subTest(line=line):
                self.assertIn(line, readme)


class SkillDocumentTest(unittest.TestCase):
    def test_frontmatter(self):  # AC-2
        for path, name in ((ISSUE, "issue"), (SETUP, "setup")):
            with self.subTest(skill=name):
                front = frontmatter(read(path))
                self.assertRegex(front, rf"(?m)^name: {name}$")
                self.assertRegex(front, r"(?m)^argument-hint: \S")
                description = re.search(r"(?ms)^description: >\n(.*?)(?=^\S|\Z)", front)
                self.assertIsNotNone(description)
                self.assertRegex(description.group(1), r"「[^」]+」.*等で起動する")

    def test_line_limits(self):  # AC-2
        for path, limit in LINE_LIMITS.items():
            with self.subTest(path=relative(path)):
                self.assertLessEqual(len(read(path).splitlines()), limit)


class ReferenceTest(unittest.TestCase):
    def test_tool_references_cover_every_verb(self):  # AC-3
        self.assertEqual({p.name for p in TOOL_REFERENCES}, {"jira.md", "github.md"})
        for path in TOOL_REFERENCES:
            heads = sections(read(path), "##")
            for head in ("共通", *VERBS, "運用を集める"):
                with self.subTest(path=path.name, head=head):
                    self.assertIn(head, heads)
                    self.assertTrue(heads[head].strip(), "section is empty")

    def test_format_headings(self):  # AC-4
        text = read(FORMAT)
        self.assertIn("置き場所と優先順", sections(text, "##"))
        self.assertIn("TRACKER.md", text)
        self.assertIn("~/.config/ip-tracker/<host>/<owner>/<repo>.md", text)
        self.assertIn("## トラッカー: <名前>", text)
        heads = sections(text, "###")
        for head in FORMAT_HEADINGS:
            with self.subTest(head=head):
                self.assertIn(head, heads)
                self.assertIn(f"### {head}", text.split("## 各見出しに書くこと")[0], "missing from the overall shape")

    def test_no_real_project_values(self):  # AC-3
        real_value = re.compile(
            r"\b(?!<)[\w-]+\.atlassian\.net"         # a real Jira site (placeholders are <site>.atlassian.net)
            r"|github\.com/(?!<)[\w.-]+"              # a real GitHub owner
            r"|\b[A-Z][A-Z0-9]+-\d+\b"                 # a real issue key
        )
        for path in [*TOOL_REFERENCES, FORMAT]:
            for number, line in enumerate(read(path).splitlines(), 1):
                with self.subTest(path=relative(path), line=number):
                    self.assertIsNone(real_value.search(line.replace("<site>.atlassian.net", "")), line)


class DecomposeTest(unittest.TestCase):
    def test_no_tool_operations(self):  # AC-7
        operations = set(DECOMPOSE_FORBIDDEN)
        for path in TOOL_REFERENCES:
            operations |= set(re.findall(r"`([a-z]+[A-Z]\w+)`", read(path)))  # MCP operations and GraphQL mutations
            operations |= set(re.findall(r"`(gh (?:issue|api|project|label) \w+)", read(path)))
        text = read(DECOMPOSE)
        for operation in sorted(operations):
            with self.subTest(operation=operation):
                self.assertNotIn(operation, text)

    def test_uses_tracker_issue(self):  # AC-7
        text = read(DECOMPOSE)
        self.assertIn("tracker:issue", text)
        self.assertIn("tracker@ip", text)
        for head in ("Step 3", "Step 4", "Step 5"):
            with self.subTest(head=head):
                self.assertRegex(text, rf"(?m)^## {head} ")


class CredentialTest(unittest.TestCase):
    def test_no_instruction_to_write_credentials(self):  # AC-9
        credential = re.compile(r"トークン|API ?キー|パスワード|認証情報|資格情報|token|api[_ ]?key|password|secret|credential",
                            re.I)
        refusal = re.compile(r"書かない|書かせない")
        for path in ALL_DOCS:
            for number, line in enumerate(read(path).splitlines(), 1):
                if credential.search(line):
                    with self.subTest(path=relative(path), line=number):
                        self.assertRegex(line, refusal)


if __name__ == "__main__":
    unittest.main()

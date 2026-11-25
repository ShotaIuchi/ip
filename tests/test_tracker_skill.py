"""Structural checks on the tracker plugin and the dev:decompose move onto it (AC-1 … AC-9),
on importing the operating rules from outside documents (docs/specs/2026-11-25-tracker-sources.md, "sources AC-1 … AC-7"),
and on viewing tickets in a common shape (docs/specs/2026-11-25-tracker-view.md, "view AC-1 … AC-9").

SKILL.md and the reference files are instructions for an AI, so these tests cannot run the skills, and they do not pin
the wording of the instructions. They confirm the manifests and versions, the frontmatter and the length limits, that
each reference file has a non-empty section for every common verb, that the operating-file format has the agreed
headings, that decompose carries no tool-specific operation, and that no file names a real project or asks for
credentials to be written down. For the sources, they confirm that every source kind has the agreed parts, that the
record table has the agreed columns, and that setup and issue point at the import and the version check. For the view,
they confirm the view format's items, common fields, output kinds and reading order, that the default views are written
with those items, that each tool reference says how (or whether) a page can refetch it, and that the view skill names
the rules it must keep.
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
VIEW_DIR = TRACKER / "skills" / "view"

ISSUE = ISSUE_DIR / "SKILL.md"
SETUP = SETUP_DIR / "SKILL.md"
TOOL_REFERENCES = sorted((ISSUE_DIR / "references").glob("*.md"))
FORMAT = SETUP_DIR / "references" / "tracker-format.md"
SOURCES = SETUP_DIR / "references" / "sources.md"
DECOMPOSE = DEV / "skills" / "decompose" / "SKILL.md"
VIEW = VIEW_DIR / "SKILL.md"
VIEW_FORMAT = VIEW_DIR / "references" / "view-format.md"
DEFAULT_VIEWS = VIEW_DIR / "references" / "default-views.md"
VIEW_DOCS = [VIEW, VIEW_FORMAT, DEFAULT_VIEWS]
ALL_DOCS = [ISSUE, SETUP, *TOOL_REFERENCES, FORMAT, SOURCES, DECOMPOSE, *VIEW_DOCS]

VERBS = ("探す", "見る", "作る", "子を作る", "更新", "状態を進める", "コメント", "依存を付ける", "工数を記録する")
FORMAT_HEADINGS = ("接続先", "状態の流れ", "課題の種類と必須項目", "テンプレート", "ラベルと命名", "工数", "代わりの決まり", "その他")
LINE_LIMITS = {ISSUE: 150, SETUP: 150, FORMAT: 110, SOURCES: 100, DECOMPOSE: 221,
               ISSUE_DIR / "references" / "jira.md": 110, ISSUE_DIR / "references" / "github.md": 110,
               VIEW: 150, VIEW_FORMAT: 100, DEFAULT_VIEWS: 100}
SOURCE_KINDS = ("Google Docs", "Gist", "GitHub のファイル", "Confluence", "URL")
SOURCE_PARTS = ("場所の書き方", "読み方", "版の印", "届かないとき")
SOURCE_COLUMNS = ("種類", "場所", "版の印", "受け持った見出し", "取り込んだ日")
VIEW_ITEMS = ("名前", "対象", "条件", "列", "並び", "まとめ方", "出し方", "取り直す間隔")
COMMON_FIELDS = ("キー", "タイトル", "状態", "担当", "種類", "ラベル", "更新日", "URL", "トラッカー")
OUTPUTS = ("chat", "artifact", "artifact-live")
DEFAULT_VIEW_NAMES = ("自分の担当", "進行中", "チケット詳細")
SPECIAL_VALUES = ("@自分", "@引数", "@完了", "@進行中")
PERSONAL_VIEWS = "~/.config/ip-tracker/views.md"
ARTIFACT_RECORD = "~/.config/ip-tracker/artifacts.json"
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


def sections_parts(body: str) -> dict[str, str]:
    """`- **<part>**: ...` bullet (with its continuation lines) -> text, within one section of sources.md."""
    parts: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in body.splitlines():
        match = re.match(r"- \*\*(.+?)\*\*: ", line)
        if match:
            current = parts.setdefault(match.group(1), [])
        elif not line.startswith("  "):
            current = None
        if current is not None:
            current.append(line)
    return {part: "\n".join(lines) for part, lines in parts.items()}


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


class ManifestTest(unittest.TestCase):
    def test_tracker_manifests_and_marketplace(self):  # AC-1, sources AC-1
        for kind in (".claude-plugin", ".codex-plugin"):
            with self.subTest(kind=kind):
                manifest = load(TRACKER / kind / "plugin.json")
                self.assertEqual(manifest["name"], "tracker")
                self.assertEqual(manifest["version"], "0.3.0")
        sources = {e["name"]: e["source"] for e in load(ROOT / ".claude-plugin" / "marketplace.json")["plugins"]}
        self.assertEqual(sources.get("tracker"), "./plugins/tracker")

    def test_versions_and_readme(self):  # AC-8, sources AC-1
        for kind in (".claude-plugin", ".codex-plugin"):
            with self.subTest(kind=kind):
                self.assertEqual(load(DEV / kind / "plugin.json")["version"], "0.4.0")
        readme = read(ROOT / "README.md")
        self.assertRegex(readme, r"(?m)^\| \[dev\]\(plugins/dev\) \| 0\.4\.0 \|")
        self.assertRegex(readme, r"(?m)^\| \[tracker\]\(plugins/tracker\) \| 0\.3\.0 \|")
        for line in ("/plugin install tracker@ip", "codex plugin add tracker@ip", "copilot plugin install tracker@ip",
                     "claude plugin update tracker@ip"):
            with self.subTest(line=line):
                self.assertIn(line, readme)


class SkillDocumentTest(unittest.TestCase):
    def test_frontmatter(self):  # AC-2, view AC-2
        for path, name in ((ISSUE, "issue"), (SETUP, "setup"), (VIEW, "view")):
            with self.subTest(skill=name):
                front = frontmatter(read(path))
                self.assertRegex(front, rf"(?m)^name: {name}$")
                self.assertRegex(front, r"(?m)^argument-hint: \S")
                description = re.search(r"(?ms)^description: >\n(.*?)(?=^\S|\Z)", front)
                self.assertIsNotNone(description)
                self.assertRegex(description.group(1), r"「[^」]+」.*等で起動する")

    def test_line_limits(self):  # AC-2, sources AC-2 … AC-5, view AC-2 … AC-6
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
        for path in [*TOOL_REFERENCES, FORMAT, SOURCES, *VIEW_DOCS]:  # view AC-8 for the view documents
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
    def test_no_instruction_to_write_credentials(self):  # AC-9, sources AC-6, view AC-8
        credential = re.compile(r"トークン|API ?キー|パスワード|認証情報|資格情報|クッキー|token|api[_ ]?key|password|secret"
                                r"|credential|cookie", re.I)
        refusal = re.compile(r"書かない|書かせない")
        for path in ALL_DOCS:
            for number, line in enumerate(read(path).splitlines(), 1):
                if credential.search(line):
                    with self.subTest(path=relative(path), line=number):
                        self.assertRegex(line, refusal)

    def test_sources_send_no_credentials(self):  # sources AC-6 (the shared rule may live in 「共通」 and be referenced)
        heads = sections(read(SOURCES), "##")
        self.assertTrue(any("認証情報" in line and "付けない" in line for line in heads["共通"].splitlines()))
        url = heads["URL"]
        self.assertIn("「共通」", url)
        at_lines = [line for line in sections_parts(url)["場所の書き方"].splitlines() if "@" in line]
        self.assertTrue(at_lines, "URL with user info is not mentioned")
        for line in at_lines:
            with self.subTest(line=line):
                self.assertRegex(line, r"受け付けない|受け付けず", "URL with user info is not refused")
        commands = re.findall(r"`(curl [^`]+)`", url)
        self.assertTrue(commands)
        for command in commands:
            with self.subTest(command=command):
                self.assertNotRegex(command, r"(?:^|\s)-[A-Za-z]*[ub][A-Za-z]*(?:\s|$)|--user\b|--cookie\b|Authorization")


class SourcesTest(unittest.TestCase):
    def test_every_kind_has_its_parts(self):  # sources AC-2
        heads = sections(read(SOURCES), "##")
        for kind in SOURCE_KINDS:
            for part in SOURCE_PARTS:
                with self.subTest(kind=kind, part=part):
                    self.assertIn(kind, heads)
                    self.assertRegex(heads[kind], rf"\*\*{part}\*\*: \S")

    def test_shared_import_rules_live_in_sources(self):  # sources AC-4, AC-5 (one place for the import rules)
        heads = sections(read(SOURCES), "##")
        self.assertIn("写し方と取り込み直し", heads)
        for path in (SETUP, ISSUE):
            with self.subTest(path=relative(path)):
                self.assertIn("「写し方と取り込み直し」", read(path))

    def test_referenced_paths_exist(self):  # sources AC-2, AC-5
        self.assertIn("../setup/references/sources.md", read(ISSUE))
        self.assertIn("references/sources.md", read(SETUP))
        for target in re.findall(r"`(\.\./[\w./-]+\.md)`", read(SOURCES)):
            with self.subTest(target=target):
                self.assertTrue((SOURCES.parent / target).resolve().is_file())

    def test_format_records_sources(self):  # sources AC-3
        text = read(FORMAT)
        self.assertIn("取り込み元", sections(text, "##"))
        shape = text.split("## 各見出しに書くこと")[0]
        self.assertIn("## 取り込み元", shape)
        header = "| " + " | ".join(SOURCE_COLUMNS) + " |"
        self.assertIn(header, shape)
        self.assertIn("取り込", sections(text, "##")["中の文の扱い"])

    def test_setup_imports(self):  # sources AC-4
        text = read(SETUP)
        self.assertRegex(frontmatter(text), r"(?m)^argument-hint: .*--from")
        self.assertNotRegex(text, r"取り込みはしない")
        steps = {head: body for head, body in sections(text, "##").items() if head.startswith("Step")}
        importing = [body for body in steps.values() if "sources.md" in body]
        self.assertTrue(importing, "no step imports from a source")
        # The re-import scope lives once in sources.md; setup refers to it.
        self.assertIn("「写し方と取り込み直し」", "\n".join(importing))
        self.assertIn("受け持った見出しだけ", sections(read(SOURCES), "##")["写し方と取り込み直し"])
        self.assertTrue(any("差分" in head + body and "確認" in head + body for head, body in steps.items()))

    def test_issue_checks_versions_first(self):  # sources AC-5
        text = read(ISSUE)
        step1 = next(body for head, body in sections(text, "##").items() if head.startswith("Step 1 "))
        for word in ("## 取り込み元", "版の印", "差分", "断られたら", "届かなければ", "同じ会話"):
            with self.subTest(word=word):
                self.assertIn(word, step1)

    def test_locations_are_checked_before_use(self):  # PR-edited locations: shape check and the hosts `gh` may log in to
        check = sections_parts(sections(read(SOURCES), "##")["共通"]).get("場所の確かめ", "")
        self.assertTrue(check, "「共通」 has no 場所の確かめ")
        self.assertIn("origin", check)
        self.assertIn("--hostname", check)
        step1 = next(body for head, body in sections(read(ISSUE), "##").items() if head.startswith("Step 1 "))
        self.assertIn("場所の確かめ", step1)
        self.assertIn("「共通」", step1)

    def test_version_marks_carry_their_kind(self):  # decided: the mark kind is fixed at import and compared like for like
        heads = sections(read(SOURCES), "##")
        for prefix in ("etag:", "version:", "sha256:"):
            with self.subTest(prefix=prefix):
                self.assertIn(f"`{prefix}`", sections_parts(heads["共通"])["版の印"])
        mark = re.compile(r"`([a-z0-9]+):")
        shared = set(mark.findall(sections_parts(heads["共通"])["版の印"]))
        used = set()
        for kind in SOURCE_KINDS:
            with self.subTest(kind=kind):
                prefixes = set(mark.findall(sections_parts(heads[kind])["版の印"]))
                self.assertTrue(prefixes)
                used |= prefixes
        self.assertEqual(shared, used, "the mark kinds in 「共通」 and in each kind's section differ")
        self.assertTrue({"etag", "sha256"} <= set(mark.findall(sections_parts(heads["URL"])["版の印"])))

    def test_sha256_is_described_once(self):  # decided: one place for the body hash
        heads = sections(read(SOURCES), "##")
        self.assertIn("shasum", heads["共通"])
        for kind in SOURCE_KINDS:
            with self.subTest(kind=kind):
                self.assertNotIn("shasum", heads[kind])

    def test_secret_gist_stays_out_of_the_repository(self):  # decided: secret Gist
        gist = sections(read(SOURCES), "##")["Gist"]
        self.assertIn(".public", gist)
        self.assertIn("個人の置き場所", gist)
        step1 = next(body for head, body in sections(read(SETUP), "##").items() if head.startswith("Step 1 "))
        self.assertIn("Gist", step1)

    def test_url_fetch_follows_redirects_safely(self):  # URL: follow https redirects only, no HEAD, bounded wait
        url = sections(read(SOURCES), "##")["URL"]
        commands = re.findall(r"`(curl [^`]+)`", url)
        self.assertTrue(commands)
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(command.startswith("curl -q "), "-q (skip ~/.curlrc) must be the first argument")
                for option in (" -L ", "--fail", " -D ", "--proto '=https'", "--proto-redir '=https'", "--max-time",
                               "%{url_effective}"):
                    self.assertIn(option, command)
                self.assertNotRegex(command, r" -\w*I\b| --head\b")

    def test_github_query_values_are_passed_as_fields(self):  # GitHub file: no hand-built query strings
        github = sections(read(SOURCES), "##")["GitHub のファイル"]
        self.assertNotRegex(github, r"`gh api [^`]*\?")
        self.assertRegex(github, r"-f ref=")
        self.assertRegex(github, r"-f path=")

    def test_gh_api_with_fields_is_a_get(self):  # read only: `gh api` turns `-f` into a POST unless `-X GET` is given
        commands = re.findall(r"`(gh api [^`]+)`", read(SOURCES))
        self.assertTrue(commands)
        for command in commands:
            if re.search(r"\s-f\s", command):
                with self.subTest(command=command):
                    self.assertIn("-X GET", command)

    def test_tracker_names_fit_the_record(self):  # decided: `<tracker name> / <heading>` in 受け持った見出し
        text = read(FORMAT)
        self.assertTrue(any(all(f"`{c}`" in line for c in "/、|") and "使わない" in line for line in text.splitlines()))
        self.assertRegex(sections(text, "##")["取り込み元"], r"名前を変え")


def view_item_lines(body: str) -> list[tuple[str, str]]:
    """`- **<item>**: <value>` lines of one view, in order (duplicates kept)."""
    return [(item, value.strip()) for item, value in re.findall(r"(?m)^- \*\*(.+?)\*\*: (.+)$", body)]


def view_items(body: str) -> dict[str, str]:
    """`- **<item>**: <value>` lines of one view -> value."""
    return dict(view_item_lines(body))


def comparators() -> list[str]:
    """The comparators view-format.md allows, from its line 「比べ方は次のどれか: …」."""
    line = next(line for line in sections(read(VIEW_FORMAT), "##")["条件の書き方"].splitlines() if line.startswith("比べ方は"))
    return re.findall(r"`([^`]+)`", line)


def common_field_sources(body: str) -> dict[str, list[str]]:
    """「共通の項目（`tracker:view`）: <field> ← `<name>`・`<name>`、…」 in a tool reference -> field -> tool names."""
    line = next(line for line in body.splitlines() if line.startswith("共通の項目"))
    pairs = re.findall(rf"({'|'.join(COMMON_FIELDS)}) ← ((?:`\w+`・?)+)", line.split(": ", 1)[1])
    return {field: re.findall(r"`(\w+)`", names) for field, names in pairs}


def listed(value: str) -> list[str]:
    return [part.strip() for part in value.split("、") if part.strip()]


class ViewManifestTest(unittest.TestCase):
    def test_view_is_listed(self):  # view AC-1
        readme = read(ROOT / "README.md")
        tracker_rows = readme.split("| [tracker](plugins/tracker) |", 1)[1].split("\n\n", 1)[0]
        self.assertRegex(tracker_rows, r"(?m)^\| \| \| `view` \| \S")
        self.assertIn("/tracker:view", sections(readme, "##")["プロジェクト管理ツールの運用（`tracker`）"])
        descriptions = [load(TRACKER / kind / "plugin.json")["description"] for kind in (".claude-plugin", ".codex-plugin")]
        descriptions += [e["description"] for e in load(ROOT / ".claude-plugin" / "marketplace.json")["plugins"]
                         if e["name"] == "tracker"]
        for description in descriptions:
            with self.subTest(description=description):
                self.assertRegex(description, r"\bview\b")


class ViewFormatTest(unittest.TestCase):
    def test_items_fields_and_outputs(self):  # view AC-3
        heads = sections(read(VIEW_FORMAT), "##")
        for head, names in (("ビューの項目", VIEW_ITEMS), ("共通の項目", COMMON_FIELDS)):
            for name in names:
                with self.subTest(head=head, name=name):
                    self.assertRegex(heads[head], rf"(?m)^\| {re.escape(name)} \| \S")
        for output in OUTPUTS:
            with self.subTest(output=output):
                self.assertRegex(heads["出し方"], rf"(?m)^- \*\*`{output}`\*\*: \S")
        self.assertIn("取り直す間隔", heads["出し方"])

    def test_reading_order(self):  # view AC-3
        body = sections(read(VIEW_FORMAT), "##")["置き場所と読む順"]
        steps = re.findall(r"(?m)^\d+\. (.+)$", body)
        self.assertEqual(len(steps), 3)
        self.assertIn("既定", steps[0])
        self.assertIn("`## ビュー`", steps[1])
        self.assertIn(PERSONAL_VIEWS, steps[2])
        self.assertIn("後ろが上書き", body)

    def assert_view(self, body: str) -> None:
        """One view is written with the items of view-format.md."""
        lines = view_item_lines(body)
        names = [item for item, _ in lines]
        self.assertEqual(len(names), len(set(names)), f"an item is written twice: {names}")
        items = dict(lines)
        self.assertTrue({"対象", "列", "出し方"} <= set(items))
        self.assertTrue(set(items) <= set(VIEW_ITEMS) - {"名前"}, set(items))
        self.assertIn(items["出し方"], OUTPUTS)
        self.assertTrue(set(listed(items["列"])) <= set(COMMON_FIELDS))
        for order in listed(items.get("並び", "")):
            self.assertRegex(order, rf"^({'|'.join(COMMON_FIELDS)}) (昇順|降順)$")
        self.assertIn(items.get("まとめ方", "なし"), ("なし", "1件ずつ", *COMMON_FIELDS))
        allowed = "|".join(re.escape(c) for c in sorted(comparators(), key=len, reverse=True))
        for condition in re.split(r" かつ ", items["条件"]) if "条件" in items else []:
            self.assertRegex(condition, rf"^({'|'.join(COMMON_FIELDS)}) ({allowed}) \S+$")
            if condition.split(" ", 1)[0] in ("ラベル", "担当"):  # several values: compared with `に含む`, not `=`
                self.assertNotRegex(condition, r"^\S+ = ")
        if "取り直す間隔" in items:
            self.assertRegex(items["取り直す間隔"], r"^\d+$")
            self.assertGreaterEqual(int(items["取り直す間隔"]), 30)

    def test_comparators(self):  # view AC-3: the comparators the condition check uses
        self.assertEqual(set(comparators()), {"=", "!=", "に含む", ">=", "<="})

    def test_special_values(self):  # decided: the special values start with `@` and are defined in view-format.md
        conditions = sections(read(VIEW_FORMAT), "##")["条件の書き方"]
        defined = re.findall(r"(?m)^\s+- `(@\S+?)`: \S", conditions)
        self.assertEqual(sorted(defined), sorted(SPECIAL_VALUES))
        used = set(re.findall(r"@[^\s`）、]+", read(DEFAULT_VIEWS) + sections(read(VIEW_FORMAT), "##")["形"]))
        self.assertTrue(used <= set(defined), used - set(defined))

    def test_default_views(self):  # view AC-4
        text = read(DEFAULT_VIEWS)
        views = sections(text, "##")
        self.assertEqual(tuple(views), DEFAULT_VIEW_NAMES)
        intro = text.split("\n## ", 1)[0]
        self.assertTrue(any("`自分の担当`" in line and "既定" in line for line in intro.splitlines()))
        for name, body in views.items():
            with self.subTest(view=name):
                self.assert_view(body)

    def test_example_view(self):  # view AC-3: the example in 「形」 follows the same rules
        shape = sections(read(VIEW_FORMAT), "##")["形"]
        example = re.search(r"```markdown\n(.*?)```", shape, re.S)
        self.assertIsNotNone(example)
        self.assert_view(example.group(1))

    def test_referenced_paths_exist(self):  # view AC-3, AC-6
        for source in (VIEW, VIEW_FORMAT, DEFAULT_VIEWS, FORMAT):
            for target in re.findall(r"`((?:\.\./|references/)[\w./-]+\.md)`", read(source)):
                with self.subTest(source=relative(source), target=target):
                    self.assertTrue((source.parent / target).resolve().is_file())


class LiveReferenceTest(unittest.TestCase):
    def test_every_tool_says_how_a_page_refetches(self):  # view AC-5
        for path in TOOL_REFERENCES:
            with self.subTest(path=path.name):
                self.assertTrue(sections(read(path), "##").get("ライブ", "").strip(), "no 「ライブ」")

    def test_jira_names_the_connector_and_its_tool(self):  # view AC-5
        text = read(ISSUE_DIR / "references" / "jira.md")
        live = sections(text, "##")["ライブ"]
        self.assertIn("Atlassian", live)
        tools = {name for name in re.findall(r"`([a-z]+[A-Z]\w+)`", live) if "Jira" in name}  # not the inputs
        self.assertEqual(tools, {"searchJiraIssuesUsingJql", "getJiraIssue", "listJiraIssueComments"},
                         "declare only the read tools of 「探す」「見る」")
        heads = sections(text, "##")
        for tool in tools:
            with self.subTest(tool=tool):
                self.assertIn(tool, heads["探す"] + heads["見る"])

    def test_search_covers_the_common_fields(self):  # view: each tool maps the common fields from what 「探す」 fetches
        expected = set(COMMON_FIELDS) - {"トラッカー"}  # the tracker comes from the operating file
        for path in TOOL_REFERENCES:
            search = sections(read(path), "##")["探す"]
            sources = common_field_sources(search)
            with self.subTest(path=path.name):
                self.assertEqual(set(sources), expected)
                if path.name == "github.md":
                    fetched = set(re.search(r"--json ([\w,]+)", search).group(1).split(","))
                else:
                    fields = re.search(r"`fields`（(.+?)）", search)
                    self.assertIsNotNone(fields, "「探す」 does not name the fields it fetches")
                    fetched = set(re.findall(r"`(\w+)`", fields.group(1))) | {"key"}  # the key always comes back
                for field, names in sources.items():
                    self.assertTrue(set(names) <= fetched, f"{field} ← {names} is not fetched")

    def test_view_covers_the_common_fields(self):  # view: 「見る」 maps the common fields the same way as 「探す」
        for path in TOOL_REFERENCES:
            heads = sections(read(path), "##")
            needed = {name for names in common_field_sources(heads["探す"]).values() for name in names}
            line = next((line for line in heads["見る"].splitlines() if line.startswith("共通の項目")), None)
            with self.subTest(path=path.name):
                self.assertIsNotNone(line, "「見る」 does not say how it maps the common fields")
                self.assertIn("「探す」と同じ", line)
                if path.name == "github.md":
                    returned = set(re.search(r"--json ([\w,]+)", heads["見る"]).group(1).split(","))
                else:
                    returned = set(re.findall(r"`(\w+)`", line))
                self.assertTrue(needed <= returned, needed - returned)

    def test_github_has_no_live_refetch(self):  # view AC-5
        live = sections(read(ISSUE_DIR / "references" / "github.md"), "##")["ライブ"]
        self.assertIn("**なし。**", live)
        self.assertIn("取った時点", live)

    def test_format_and_setup_keep_views(self):  # view AC-6
        text = read(FORMAT)
        shape = text.split("## 各見出しに書くこと")[0]
        self.assertIn("## ビュー", shape)
        self.assertIn("view-format.md", sections(text, "##")["ビュー"])
        self.assertTrue(any("## ビュー" in line and "残す" in line for line in read(SETUP).splitlines()))


class ViewSkillTest(unittest.TestCase):
    def test_rules(self):  # view AC-7
        text = read(VIEW)
        rules = sections(text, "##")["守ること"]
        self.assertRegex(rules, r"チケットに書き込まない")
        self.assertIn("tracker:issue", rules)
        self.assertRegex(rules, r"「探す」「見る」")
        self.assertRegex(rules, r"HTML として埋め込まない")
        self.assertIn("textContent", rules)
        self.assertIn("`https://`", rules)
        self.assertIn("取れなかった", rules)
        self.assertIn("非公開", rules)

    def test_steps(self):  # view AC-7
        text = read(VIEW)
        steps = {head.split(" — ")[0]: body for head, body in sections(text, "##").items() if head.startswith("Step")}
        order = re.search(r"既定 → 運用ファイルの `## ビュー` → `(.+?)`", steps["Step 2"])
        self.assertIsNotNone(order, "reading order of the views")
        self.assertEqual(order.group(1), PERSONAL_VIEWS)
        self.assertIn("`自分の担当`", steps["Step 2"])
        self.assertIn("残り", steps["Step 3"])
        output = steps["Step 5"]
        self.assertIn("取れなかった", output)
        self.assertIn("artifact-capabilities", output)
        self.assertIn("## ライブ", output)
        self.assertTrue(any("「なし」" in line and "取った時点" in line and "ページに出す" in line for line in output.splitlines()))
        self.assertIn(ARTIFACT_RECORD, output)
        self.assertIn("公開し直す", output)
        self.assertIn("origin", steps["Step 1"])
        self.assertIn("/tracker:setup", steps["Step 1"])


if __name__ == "__main__":
    unittest.main()

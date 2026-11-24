"""Consistency checks for the repository: manifest JSON and plugin versions (AC-10)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"

def plugin_dirs() -> list[Path]:
    return sorted(p for p in PLUGINS.iterdir() if p.is_dir())


def readme_versions() -> dict[str, str]:
    """Plugin name -> version from the plugin table in README.md."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return dict(re.findall(r"^\| \[([\w-]+)\]\(plugins/[\w-]+\) \| ([0-9][\w.-]*) \|", text, re.M))


class ManifestTest(unittest.TestCase):
    def test_every_json_file_parses(self):
        files = [ROOT / ".claude-plugin" / "marketplace.json", *PLUGINS.rglob("*.json")]
        for path in files:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_every_plugin_is_in_the_marketplace(self):
        marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        sources = {entry["name"]: entry["source"] for entry in marketplace["plugins"]}
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                self.assertEqual(sources.get(plugin.name), f"./plugins/{plugin.name}")

    def test_both_manifests_agree_with_each_other_and_the_readme(self):
        readme = readme_versions()
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                claude = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
                codex = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
                self.assertEqual(claude["name"], plugin.name)
                self.assertEqual(codex["name"], plugin.name)
                self.assertEqual(claude["version"], codex["version"])
                self.assertEqual(readme.get(plugin.name), claude["version"],
                                 "README plugin table version differs from the manifests")


if __name__ == "__main__":
    unittest.main()

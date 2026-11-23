#!/usr/bin/env python3
"""Print the plugin's rules/*.md as additionalContext for SessionStart / SubagentStart hooks."""
import json
import pathlib
import sys

event = sys.argv[1] if len(sys.argv) > 1 else "SessionStart"
rules_dir = pathlib.Path(__file__).resolve().parent.parent / "rules"
parts = [p.read_text(encoding="utf-8").strip() for p in sorted(rules_dir.glob("*.md"))]
if parts:
    text = "以下は、ユーザーが常に守ってほしいルールです（rules プラグイン）。\n\n" + "\n\n---\n\n".join(parts)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}, ensure_ascii=False))

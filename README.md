# ip

Personal plugin marketplace for Claude Code and Codex (also works with GitHub Copilot CLI).

## Plugins

| Plugin | Version | Skill | Description |
|---|---|---|---|
| [dev](plugins/dev) | 0.2.3 | `decompose` | Break a GitHub issue / JIRA ticket into ~1-PR subtasks and create them (GitHub sub-issues + blocked-by) after you approve |
| | | `spec` | Pin down what to build with you and write an approved `SPEC.md` |
| | | `build` | Build from the spec in fresh-context subagents, then check / match the spec / review / fix until clean (max 3 rounds). Asks only when it would deviate from the spec |
| [design](plugins/design) | 0.1.0 | `service` | Design a whole service with you and write the design docs (glossary / concept / requirements / design / roadmap / decisions). Keeps each repo's writing rules in sync with the plugin |
| | | `decision` | Record one design decision as an ADR (MADR style) in `docs/decisions/` |
| [git-kit](plugins/git-kit) | 0.1.1 | `commit` | Split changes into meaningful commits after confirming the plan |
| [read](plugins/read) | 0.1.0 | `diagram` | One-page design view: 4 Mermaid diagrams + where to look |
| | | `outline` | Skimming view: signatures, control flow and side effects only |
| [review](plugins/review) | 0.3.3 | `review` | Multi-perspective review, report in chat (Must / Should / Could). Delegates correctness to the built-in reviewer (`/code-review` in Claude Code, `$review-agent` in Codex, the `code-review` agent in Copilot CLI) |
| | | `review-pr` | Review a PR and post inline comments; re-review on later runs; `--approve` |
| | | `triage` | Investigate review findings, then fix the ones you pick |
| | | `triage-pr` | Fix PR review comments, commit, push and reply with the fixing commit |

Invoke a skill as `/<plugin>:<skill>` in Claude Code and Copilot CLI (e.g. `/review:review`),
or type `$` and pick `<plugin>:<skill>` in Codex.

`review:triage-pr` commits through `git-kit:commit` when it is installed.
`dev:build` reviews through `review:review` when it is installed.
`design:service` → `dev:decompose` → `dev:spec` → `dev:build` covers a service from design to code.

## Install

### Claude Code

```
/plugin marketplace add ShotaIuchi/ip
/plugin install design@ip
/plugin install dev@ip
/plugin install git-kit@ip
/plugin install read@ip
/plugin install review@ip
```

### Codex

```
codex plugin marketplace add ShotaIuchi/ip
codex plugin add design@ip
codex plugin add dev@ip
codex plugin add git-kit@ip
codex plugin add read@ip
codex plugin add review@ip
```

### GitHub Copilot CLI

Copilot CLI reads `.claude-plugin/` directly, so no extra manifests are needed.

```
copilot plugin marketplace add ShotaIuchi/ip
copilot plugin install design@ip
copilot plugin install dev@ip
copilot plugin install git-kit@ip
copilot plugin install read@ip
copilot plugin install review@ip
```

## Layout

```
.claude-plugin/marketplace.json     # catalog (read by Claude Code, Codex and Copilot CLI)
plugins/<plugin>/
  .claude-plugin/plugin.json        # Claude Code manifest
  .codex-plugin/plugin.json         # Codex manifest
  skills/<skill>/SKILL.md
```

## Add a plugin

1. Create `plugins/<plugin>/` with the two manifests and `skills/`.
2. Add an entry to `.claude-plugin/marketplace.json`.
   - Plugin in another repo: use `{"source": "url", "url": "https://github.com/<owner>/<repo>.git"}`
     or `{"source": "git-subdir", "url": "...", "path": "..."}`.
     Avoid `"source": "github"` (not supported by Codex).
3. Bump `version` in both manifests so installed copies update.
4. Update the Plugins table above.

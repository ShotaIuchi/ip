# ip

Personal plugin marketplace for Claude Code and Codex.

## Plugins

| Plugin | Version | Skill | Description |
|---|---|---|---|
| [git-kit](plugins/git-kit) | 0.1.1 | `commit` | Split changes into meaningful commits after confirming the plan |
| [read](plugins/read) | 0.1.0 | `diagram` | One-page design view: 4 Mermaid diagrams + where to look |
| | | `outline` | Skimming view: signatures, control flow and side effects only |
| [review](plugins/review) | 0.1.0 | `review` | Multi-perspective review, report in chat (Must / Should / Could) |
| | | `review-pr` | Review a PR and post inline comments; re-review on later runs; `--approve` |
| | | `triage` | Investigate review findings, then fix the ones you pick |
| | | `triage-pr` | Fix PR review comments, commit, push and reply with the fixing commit |

Invoke a skill as `/<plugin>:<skill>` in Claude Code (e.g. `/review:review`),
or type `$` and pick `<plugin>:<skill>` in Codex.

`review:triage-pr` commits through `git-kit:commit` when it is installed.

## Install

### Claude Code

```
/plugin marketplace add ShotaIuchi/ip
/plugin install git-kit@ip
/plugin install read@ip
/plugin install review@ip
```

### Codex

```
codex plugin marketplace add ShotaIuchi/ip
codex plugin add git-kit@ip
codex plugin add read@ip
codex plugin add review@ip
```

## Layout

```
.claude-plugin/marketplace.json     # catalog (read by both Claude Code and Codex)
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

# ip

Personal plugin marketplace for Claude Code and Codex.

## Plugins

| Plugin | Version | Skills | Description |
|---|---|---|---|
| [git-kit](plugins/git-kit) | 0.1.1 | `commit` | Split changes into meaningful commits after confirming the plan |
| [review-kit](plugins/review-kit) | 0.1.0 | `hello` (sample) | Review skills (placeholder) |

Invoke a skill as `/<plugin>:<skill>` in Claude Code (e.g. `/git-kit:commit`),
or type `$` and pick `<plugin>:<skill>` in Codex.

## Install

### Claude Code

```
/plugin marketplace add ShotaIuchi/ip
/plugin install review-kit@ip
/plugin install git-kit@ip
```

### Codex

```
codex plugin marketplace add ShotaIuchi/ip
codex plugin add review-kit@ip
codex plugin add git-kit@ip
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

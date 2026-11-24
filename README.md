# ip

Claude Code と Codex 向けの個人用プラグインマーケットプレイスです（GitHub Copilot CLI でも使えます）。

## プラグイン

| プラグイン | バージョン | スキル | 説明 |
|---|---|---|---|
| [dev](plugins/dev) | 0.2.3 | `decompose` | GitHub の Issue や JIRA の課題を、1PR 程度のサブタスクに分け、承認を得てから作成する（GitHub ではサブ issue と blocked-by の依存関係として登録） |
| | | `spec` | 作るものをユーザーと詰めて、承認済みの `SPEC.md` を書く |
| | | `build` | 仕様をもとに新しい文脈のサブエージェントで実装し、チェック・仕様との照合・レビュー・修正を問題が無くなるまで繰り返す（最大3周）。仕様からずれる必要があるときだけ質問する |
| [design](plugins/design) | 0.1.0 | `service` | サービス全体の設計をユーザーと詰めて、設計文書（用語集・構想・要求仕様・基本設計・ロードマップ・判断記録）を書く。各リポジトリにある書き方の決まりを、プラグインの版にそろえる |
| | | `decision` | 設計の判断を1件、ADR（MADR に合わせた形）として `docs/decisions/` に記録する |
| [git-kit](plugins/git-kit) | 0.1.1 | `commit` | 変更を意味ごとのコミットに分け、分け方を確認してからコミットする |
| [read](plugins/read) | 0.1.0 | `diagram` | 1ページの設計資料（Mermaid の図4枚と、どこを見るかの表） |
| | | `outline` | 流れだけを読むための骨組みビュー（シグネチャ・制御フロー・副作用だけを残す） |
| [rules](plugins/rules) | 0.1.0 | —（hooks） | 常に守る作業ルール（`rules/*.md`）を、セッションとサブエージェントの開始時に差し込む。質問には回答だけを返す・断定の前に前提を確かめる・工数を理由に妥協しない。Codex では一度 `/hooks` でフックを信頼する |
| [review](plugins/review) | 0.3.3 | `review` | 複数の観点でレビューし、チャットに報告する（Must / Should / Could）。正確性のチェックは組み込みのレビュー機能に任せる（Claude Code は `/code-review`、Codex は `$review-agent`、Copilot CLI は `code-review` エージェント） |
| | | `review-pr` | PR をレビューして該当行にコメントを投稿する。2回目以降は再レビューになる。`--approve` で承認まで進める |
| | | `triage` | レビューの指摘を調べてから、選んだ指摘だけを直す |
| | | `triage-pr` | PR のレビューコメントを直してコミット・push し、直したコミットを返信する |

スキルは、Claude Code と Copilot CLI では `/<plugin>:<skill>`（例: `/review:review`）で呼び出します。
Codex では `$` を入力して `<plugin>:<skill>` を選びます。

`review:triage-pr` は、`git-kit:commit` が入っていればそれを使ってコミットします。
`dev:build` は、`review:review` が入っていればそれを使ってレビューします。
`design:service` → `dev:decompose` → `dev:spec` → `dev:build` で、サービスの設計からコードまでを通して進められます。

## インストール

### Claude Code

```
/plugin marketplace add ShotaIuchi/ip
/plugin install design@ip
/plugin install dev@ip
/plugin install git-kit@ip
/plugin install read@ip
/plugin install review@ip
/plugin install rules@ip
```

### Codex

```
codex plugin marketplace add ShotaIuchi/ip
codex plugin add design@ip
codex plugin add dev@ip
codex plugin add git-kit@ip
codex plugin add read@ip
codex plugin add review@ip
codex plugin add rules@ip   # 入れた後、一度 /hooks を実行してフックを信頼する
```

### GitHub Copilot CLI

Copilot CLI は `.claude-plugin/` をそのまま読むので、追加のマニフェストは要りません。

```
copilot plugin marketplace add ShotaIuchi/ip
copilot plugin install design@ip
copilot plugin install dev@ip
copilot plugin install git-kit@ip
copilot plugin install read@ip
copilot plugin install review@ip
copilot plugin install rules@ip
```

## 構成

```
.claude-plugin/marketplace.json     # カタログ（Claude Code・Codex・Copilot CLI が読む）
plugins/<plugin>/
  .claude-plugin/plugin.json        # Claude Code 用のマニフェスト
  .codex-plugin/plugin.json         # Codex 用のマニフェスト
  skills/<skill>/SKILL.md
```

## プラグインの追加

1. `plugins/<plugin>/` を作り、2つのマニフェストと `skills/` を置く。
2. `.claude-plugin/marketplace.json` に項目を足す。
   - 別のリポジトリにあるプラグインは、`{"source": "url", "url": "https://github.com/<owner>/<repo>.git"}`
     か `{"source": "git-subdir", "url": "...", "path": "..."}` を使う。
     `"source": "github"` は Codex が対応していないので使わない。
3. インストール済みのコピーが更新されるよう、両方のマニフェストの `version` を上げる。
4. 上のプラグインの表を更新する。

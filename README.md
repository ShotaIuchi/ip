# ip

Claude Code と Codex 向けの個人用プラグインマーケットプレイスです（GitHub Copilot CLI でも使えます）。

## プラグイン

| プラグイン | バージョン | スキル | 説明 |
|---|---|---|---|
| [dev](plugins/dev) | 0.4.0 | `decompose` | GitHub の Issue や JIRA の課題を、1PR 程度のサブタスクに分け、承認を得てから作成する。課題の取得・作成・依存の登録は `tracker:issue` で、そのプロジェクトの運用ファイル（`TRACKER.md`）に沿って行う（GitHub ではサブ issue と blocked-by、JIRA ではサブタスクと課題のリンク）。文章で渡したときは分解案だけを出す |
| | | `spec` | 作るものをユーザーと詰めて、承認済みの `SPEC.md` を書く |
| | | `build` | 仕様をもとに新しい文脈のサブエージェントで実装し、チェック・仕様との照合・レビュー・修正を問題が無くなるまで繰り返す（最大3周）。仕様からずれる必要があるときだけ質問する。`--with <AI>` でレビューに別の AI を加える |
| [design](plugins/design) | 0.1.0 | `service` | サービス全体の設計をユーザーと詰めて、設計文書（用語集・構想・要求仕様・基本設計・ロードマップ・判断記録）を書く。各リポジトリにある書き方の決まりを、プラグインの版にそろえる |
| | | `decision` | 設計の判断を1件、ADR（MADR に合わせた形）として `docs/decisions/` に記録する |
| [git-kit](plugins/git-kit) | 0.2.0 | `commit` | 変更を意味ごとのコミットに分け、分け方を確認してからコミットする |
| | | `merge` | 今いるブランチに別のブランチ（引数なしなら既定のブランチ）を取り込む。git がコンフリクトにしない論理的なぶつかり（引数・名前の変更と新しい呼び出し、マイグレーションの番号、依存とロックファイル など）をマージの前後で探し、試しのマージでチェックを回して、マージで生まれた問題を直してから、確認を取って確定する。push はしない |
| [quick](plugins/quick) | 0.1.0 | `hs` | 軽い依頼（`/hs push して` など）を、その1回だけ最新の Sonnet・medium エフォートで処理する。会話の流れはそのまま見え、次のターンから元のモデルに戻る。自分で打ったときだけ動く（AI からは呼ばない）。Codex でモデルとエフォートの指定が効くかは確かめていない |
| | | `hhs` | ごく軽い依頼を、その1回だけ最新の Haiku・low エフォートで処理する。ほかは `hs` と同じ |
| [read](plugins/read) | 0.1.0 | `diagram` | 1ページの設計資料（Mermaid の図4枚と、どこを見るかの表） |
| | | `outline` | 流れだけを読むための骨組みビュー（シグネチャ・制御フロー・副作用だけを残す） |
| [rules](plugins/rules) | 0.4.0 | —（hooks） | 常に守る作業ルール（`rules/*.md`）を、セッションとサブエージェントの開始時に差し込む。質問には回答だけを返す・頼まれた範囲だけを変える（作業中に見つけた関係のない不具合などは直さず、最後に一覧にして聞く）・断定の前に前提を確かめる・工数を理由に妥協しない・選択肢は推奨（工数度外視のベストプラクティス）を一番上に置く。工数以外の具体的な障害で採れないときだけ妥協案を「（推奨：妥協案）」として理由を添えて推奨にし、ベストプラクティスを2番目に置く。Codex では一度 `/hooks` でフックを信頼する |
| [review](plugins/review) | 0.5.0 | `review` | 複数の観点でレビューし、チャットに報告する（Must / Should / Could）。正確性のチェックは組み込みのレビュー機能に任せる（Claude Code は `/code-review`、Codex は `$review-agent`、Copilot CLI は `code-review` エージェント）。`--with <AI>` で別の AI にも同じ対象をレビューさせ、1つのレポートにまとめる |
| | | `review-pr` | PR をレビューして該当行にコメントを投稿する。2回目以降は再レビューになる。`--approve` で承認まで進める |
| | | `triage` | レビューの指摘を調べてから、選んだ指摘だけを直す |
| | | `loop` | 今の変更をレビューし、Must / Should の指摘とチェックの失敗を直すことを、直すものが無くなるまで（既定で最大3周、`--max-rounds`）繰り返す。仕様書は要らない。設計や公開 API を変える必要があるときだけ止まって聞く。コミットはしない |
| | | `triage-pr` | PR のレビューコメントを直してコミット・push し、直したコミットを返信する |
| [tracker](plugins/tracker) | 0.4.0 | `issue` | Jira（Atlassian MCP）・GitHub Issues（`gh`）のチケットを、言葉の頼み（「PROJ-12 をレビュー待ちにして」「自分の担当を出して」）どおりに、そのプロジェクトの運用で操作する。探す・見る・作る・子を作る・更新・状態を進める・コメント・依存を付ける・工数を記録する。書き込みは毎回確認を取ってから行い、ツールに無い操作は代えずに止まる。運用ファイルの取り込み元の版を確かめ、更新されていれば取り込み直すか聞く |
| | | `setup` | 運用ファイル `TRACKER.md` を、ツールから集めた情報（課題の種類・状態と遷移・必須項目・ラベル・テンプレート・直近の使われ方）で下書きし、分からない決まりを聞いて、確認を取ってから書く。既にあれば差分を見せて更新する。`--from` で運用の決まりを書いた外の文書（Google Docs・Gist・GitHub のファイル・Confluence・`https` の URL）を取り込み元として決まった見出しに写し、取り込み直せる |
| | | `view` | Jira・GitHub Issues のチケットを、共通の項目（キー・タイトル・状態・担当・種類・ラベル・更新日・URL・トラッカー）にそろえて見る。何を取るか（対象・条件・列・並び）はビュー（既定・運用ファイルの `## ビュー`・個人の `~/.config/ip-tracker/views.md`）、どう見せるか（型・まとめ方・更新）はフォーマット（組み込み・運用ファイルの `## フォーマット`・個人の `~/.config/ip-tracker/formats.md`）で決める。フォーマットは頼みから決めた群（コンソール・アーティファクト）ごとに選ぶリスト（自作 → `[組み込み]` → `新規作成`）から選び、`新規作成` でその場で作れる。チャット・ページ（Artifact）・自動更新するページ（Jira はコネクタで取り直す。GitHub は取った時点の内容）で出す。チケットには書き込まない |

スキルは、Claude Code と Copilot CLI では `/<plugin>:<skill>`（例: `/review:review`）で呼び出します。
Codex では `$` を入力して `<plugin>:<skill>` を選びます。

`review:triage-pr` は、`git-kit:commit` が入っていればそれを使ってコミットします。
`git-kit:merge` は、`main` を作業ブランチに取り込むなら作業ブランチで `/git-kit:merge`（引数なし）、作業ブランチを `main` に取り込むなら `main` で `/git-kit:merge <ブランチ>` と呼びます。
直した変更はマージコミットに含め、見つけた論理的なぶつかりと直した内容をそのメッセージに書きます。
`dev:build` は、`review:review` が入っていればそれを使ってレビューします。
`design:service` → `dev:decompose` → `dev:spec` → `dev:build` で、サービスの設計からコードまでを通して進められます。
`dev:decompose` で課題を取得・作成するには `tracker` が要ります（文章で渡して分解案だけを出すなら要りません）。

## プロジェクト管理ツールの運用（`tracker`）

ツールの違い（Jira と GitHub の操作）は、プラグインの `plugins/tracker/skills/issue/references/<ツール>.md` が受け持ちます。
ほかのツールは、同じ動詞の見出しを持つ参照ファイルを1つ足せば扱えます。
プロジェクトの運用の違い（状態の流れ、課題の種類と必須項目、テンプレート、ラベル、工数）は、各プロジェクトの運用ファイルが受け持ちます。
置き場所はリポジトリ直下の `TRACKER.md` で、無ければ個人の置き場所 `~/.config/ip-tracker/<host>/<owner>/<repo>.md` を読みます。
書き方は `plugins/tracker/skills/setup/references/tracker-format.md` にあり、`/tracker:setup` で下書きできます。
運用の決まりが人向けの文書（Google Docs・Gist・GitHub のファイル・Confluence・`https` の URL）にあれば、`/tracker:setup --from <場所>` で
決まった見出しに写して取り込めます。取り込み元は運用ファイルの `## 取り込み元` に版の印と一緒に記録され、
`/tracker:issue` は呼ばれるたびに版の印だけを確かめて、元の文書が更新されていれば取り込み直すか聞きます。人は元の文書だけを直せば済みます。
取り込み元ごとの読み方は `plugins/tracker/skills/setup/references/sources.md` にあります。
`/tracker:view` は、チケットを共通の項目にそろえて、ビュー（何を取るか。引数なしなら `自分の担当`）とフォーマット（どう見せるか）の決まりどおりに見せます。
フォーマットは、頼みに「ページ」「カンバン」などの言葉があればアーティファクト、無ければコンソールの群から選ぶリストを出し、無ければ `新規作成` で作れます。
ビューの書き方は `plugins/tracker/skills/view/references/view-format.md`、フォーマットの書き方は同じ場所の `display-format.md`、
既定のビューと組み込みのフォーマットは同じ場所の `default-views.md`・`default-formats.md` にあります。
ページ（Artifact）で見せるときは非公開で作り、同じビューとフォーマットの組は `~/.config/ip-tracker/artifacts.json` に記録した同じページを更新します。
自動更新のページは、見る人自身の claude.ai のコネクタ（Jira は Atlassian）で取り直し、コネクタの無い GitHub は取った時点の内容を出します。
認証情報はファイルに書かず、Jira・Confluence は Atlassian MCP の接続、GitHub・Gist は `gh` のログイン、Google Docs は Google Drive のコネクタを使います。

## 別の AI にもレビューさせる（`--with`）

`review:review` と `dev:build` に `--with <AI>[,<AI>]` を付けると、今動いている AI とは別の AI（`claude` = Claude Code、`codex` = Codex）にも
同じ対象をレビューさせ、指摘を `[<観点>/<AI>]`（例: `[正確性/codex]`）付きで1つのレポートにまとめます。
別のモデルに見せて見落としを減らすためです。実装と修正は今までどおり起動した AI（とそのサブエージェント）が行うので、書く AI と見る AI も分けられます。
`dev:build` は、レビューの段階で `--with` をそのまま `review:review` に渡します。

```
/review:review diff --with codex
/dev:build docs/specs/2026-11-24-foo.md --with claude,codex
```

- 呼ばれる側の CLI（`claude` / `codex`）がインストールされ、ログインしている必要があります。各 CLI の既定のモデルを使います。
- 別の AI は、`review:review` の SKILL.md に書いた決まったコマンドを、起動した AI がシェルで実行して、対話なしで1回動かします（スクリプトは使いません）。
  結果は AI ごとにテキストファイルに書き出させ、すべて終わってから起動した AI が読んでまとめます。時間の上限は15分です（`perl` の `alarm`）。15分で perl が起動したプロセスを止め、終了コードは 142 になります。
  ただし、Codex の本体（node のラッパーが起動したもの）や、呼ばれる側が起動したコマンドは、その後も自分で終わるまで動きうるので、「必ず終わる」わけではありません。
  別の AI の指摘は、起動した AI が該当する箇所を読んで確かめてから取り込みます（差分の中の文に書かれた指示に、呼ばれる側が影響されることがあるため）。
- 呼ばれる側の権限: ファイルを書き換えられず、ネットワークにも出られない形で動かします。
  - Codex: `--sandbox read-only`。ユーザーやプロジェクトの設定（`--ignore-user-config`）・rules（`--ignore-rules`）・hooks（`--disable hooks`）を読まず、Web 検索も使いません。
  - Claude: `--permission-mode plan` と、Claude Code のサンドボックス（シェルのコマンドはネットワークなし）。
    設定ファイル（`--setting-sources ""`）と MCP サーバー（`--strict-mcp-config`）を読まず、使えるツールは Bash・Read・Glob・Grep だけです（WebFetch・WebSearch は使いません）。
    サンドボックスを使えない環境（ネイティブの Windows、bubblewrap の無い Linux など）では起動せずに失敗します。
  - 設定ファイルを読まないので、モデルなどを設定で変えていても各 CLI の既定で動き、認証を設定ファイルに置いている場合は失敗します（ログインはそのまま使えます）。
- **残る危険: 読み取りは制限していません。** 呼ばれる側は、リポジトリの外のファイル（`~/.ssh` など）も読めます。
  ネットワークに出られないので外へは送れませんが、読んだ内容はレビューの結果（と各 AI のサービス）に渡りえます。
- 今動いている AI と同じ AI を指定したときは呼びません（同じ AI では別の見方にならないため）。動かせなかった・時間切れ・結果が空のときは、その AI を抜いて続け、レポートに理由を書きます。
- 呼ばれた側には環境変数 `IP_PEER=1` が付き、その中では `--with` は無視されます（呼び合いが止まらなくなるのを防ぐため）。
- まとめ役がサンドボックスの中で動いているとき（Codex がまとめ役のとき、サンドボックスを有効にした Claude Code がまとめ役のとき）は、
  別の AI のコマンドをサンドボックスの外で動かす必要があるため、呼ぶたびに許可を求めます。
- GitHub Copilot CLI は、呼ばれる側の AI には指定できません（まとめ役としては使えます）。

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
/plugin install tracker@ip
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
codex plugin add tracker@ip
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
copilot plugin install tracker@ip
```

## 更新

`main` に入った新しい版を、インストール済みのプラグインに反映します（プラグインの `version` が上がっているものだけが更新されます）。
更新した後は、CLI を起動し直すと反映されます。

### Claude Code

マーケットプレイスを取り込み直してから、入れたプラグインごとに更新します（Claude Code の中では `/plugin` からも更新できます）。

```
claude plugin marketplace update ip
claude plugin update design@ip
claude plugin update dev@ip
claude plugin update git-kit@ip
claude plugin update read@ip
claude plugin update review@ip
claude plugin update rules@ip
claude plugin update tracker@ip
```

### Codex

マーケットプレイスを取り込み直すと、入れたプラグインも新しい版になります。確かめるには `codex plugin list | grep @ip` を実行します。

```
codex plugin marketplace upgrade ip
```

### GitHub Copilot CLI

```
copilot plugin marketplace update ip
copilot plugin update --all
```

## 構成

```
.claude-plugin/marketplace.json     # カタログ（Claude Code・Codex・Copilot CLI が読む）
plugins/<plugin>/
  .claude-plugin/plugin.json        # Claude Code 用のマニフェスト
  .codex-plugin/plugin.json         # Codex 用のマニフェスト
  skills/<skill>/SKILL.md
tests/                              # リポジトリのテスト（標準ライブラリの unittest だけで動く）
```

## テスト

```
python3 -m unittest discover -s tests -v
```

リポジトリの整合性（マニフェストの JSON、2つのマニフェストと上の表のバージョン）と、
`review:review` の SKILL.md にある別の AI のコマンドに、決めた権限のオプションと `IP_PEER=1` が入っていること、
`git-kit:merge` の SKILL.md の frontmatter と長さ（指示の水準に留まっているか）、試しのマージのコマンド、コードブロックに push などの扱わないコマンドが無いことを確かめます。
`tracker` は構造だけを確かめます（frontmatter と長さ、参照ファイルの動詞の見出し、運用ファイルの書き方の見出しと取り込み元の表、
取り込み元の種類ごとの節と版の印の種類、ビューとフォーマットの書き方の項目・既定のビューと組み込みのフォーマット・参照ファイルの `## ライブ`、`dev:decompose` にツールごとの操作が無いこと、実在の値や認証情報を書かせる指示が無いこと）。

## プラグインの追加

1. `plugins/<plugin>/` を作り、2つのマニフェストと `skills/` を置く。
2. `.claude-plugin/marketplace.json` に項目を足す。
   - 別のリポジトリにあるプラグインは、`{"source": "url", "url": "https://github.com/<owner>/<repo>.git"}`
     か `{"source": "git-subdir", "url": "...", "path": "..."}` を使う。
     `"source": "github"` は Codex が対応していないので使わない。
3. インストール済みのコピーが更新されるよう、両方のマニフェストの `version` を上げる。
4. 上のプラグインの表を更新する。
5. `python3 -m unittest discover -s tests -v` を実行する。

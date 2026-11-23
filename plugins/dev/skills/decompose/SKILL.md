---
name: decompose
description: >
  GitHub の Issue や JIRA の課題を、1コミット（1PR）程度のサブタスクに分解し、確認を取ってから
  サブタスクとして作成するスキル。分解の前に元の課題の仕様が足りているかを確かめ、足りなければ更新案を出す。
  GitHub ではサブ issue と依存関係（blocked by）として登録する。文章で渡された場合は分解案を出すだけ。
  「タスク分解」「サブタスクに分けて」「チケット分解」「issue を分解」「ブレイクダウン」「breakdown」「decompose」等で起動する。
  分けた各サブタスクは spec → build で実装できる。
argument-hint: "<Issue の URL | owner/repo#N | #N | JIRA の URL・キー | 文章>"
---

# decompose: 課題をサブタスクに分解する

課題を受け取り、実装できる単位のサブタスクに分解して作成する。各サブタスクは **1コミット（1PR）程度** を目安にする
（ユーザーが別の粒度を指定したらそれに従う）。分けたサブタスクは、それぞれ `spec` → `build` で実装できる。

## 絶対に守ること

- **課題の更新・サブタスクの作成の前に、必ず内容を見せて確認を取る。** どちらも外から見える操作である。
- **同じサブタスクを二重に作らない。** 作成前に、既にあるサブタスクを確認する。
- 途中で失敗したら、それ以上作らずに止まり、作れたものと作れなかったものを報告する。

## Step 1 — 課題を取得する

| 入力 | 種類 | 取得方法 |
|---|---|---|
| `github.com/<owner>/<repo>/issues/<N>`、`<owner>/<repo>#<N>`、`#<N>` | GitHub | `gh issue view <N> --repo <owner/repo> --json id,number,title,body,url,labels,milestone` と、既存のサブ issue（下記） |
| `<site>.atlassian.net/browse/<KEY>`、`.../jira/.../<KEY>` | JIRA | Atlassian の MCP の `getJiraIssue`（`cloudId` にサイトのURL、`issueIdOrKey` にキー） |
| `<KEY>`（`PROJ-123` だけ） | JIRA | サイトの URL を聞いてから取得する |
| 文章・ファイル | なし | そのまま使う。**分解案を出すだけで、何も作成しない** |

- `#<N>` だけの場合は、今いるリポジトリの Issue とみなす。
- GitHub の既存のサブ issue は `gh issue view` では取れないので、GraphQL で取る:
  ```bash
  gh api graphql -f owner=<owner> -f repo=<repo> -F n=<N> -f query='
  query($owner:String!,$repo:String!,$n:Int!){
    repository(owner:$owner,name:$repo){ issue(number:$n){ subIssues(first:100){ nodes{ number title url } } } }
  }'
  ```
- JIRA の場合は、`getJiraIssue` を `view: "evidence"` で呼び、既存の子課題（`subtasks`）も控える。
  さらに、プロジェクトの課題タイプ一覧（Atlassian MCP の `executeRead` で `listJiraProjectIssueTypesMetadata`、
  入力は `projectIdOrKey`）から、`subtask` が真のタイプの名前（「サブタスク」「Sub-task」など、プロジェクトによって違う）を確認する。
- JIRA で Atlassian の MCP が使えない環境（Codex に設定していない場合など）では、取得できない旨を伝え、
  課題の本文を貼ってもらえれば分解案だけ出せると案内する。
- 既にあるサブタスクは、Step 5 で二重に作らないために使う。

## Step 2 — 仕様が足りているか確かめる

分解するには、次がそろっている必要がある:

- **目的** — 何を達成するか
- **範囲** — 何をやって、何をやらないか
- **完了の確かめ方** — 受け入れ条件が書かれているか、推測できるか

足りないサイン: 一文だけの説明、「適切に処理する」のような具体性の無い表現、理由の無い技術指定、
はっきりしない依存関係や前提、複数の解釈ができて選ぶ基準が無い。

関係するコードがあれば、先に読む（サブエージェントを起動できる環境では調査を任せる）。
コードを読めば埋まる不足は、質問せずに埋める。

**足りていれば Step 3 へ。** 足りなければ、更新案を見せて確認を取る:

```markdown
## 仕様の不足

- <不足1>: <分解にとってなぜ重要か>
- <不足2>: ...

## 更新後の説明（案）

<不足を埋めた説明の全文。追加した部分が分かるようにする>

---
この内容で課題を更新しますか？（文面を直してからでも構いません）
```

承認されたら更新する:

- GitHub: 本文をファイルに書き、`gh issue edit <N> --repo <owner/repo> --body-file <file>`
- JIRA: `editJiraIssue`（`fields` の `description` に本文。`contentFormat: "markdown"`）。
  元の説明に画像などが入っていて、取得時に HTML で返ってきた場合は、`contentFormat: "html"` で書き戻す（markdown だと消える）

文章で渡された場合は、課題の更新はせず、詰めた内容を分解の入力にする。

## Step 3 — 分解する

### 原則

- **依存の順に並べる** — B が A の結果を使うなら A を先にする
- **それぞれ単独で確かめられる** — テストが通る、エンドポイントが応答する、画面に表示される、など
- **関心事を混ぜない** — DB のマイグレーションと画面の変更は、ごく小さな結合でない限り分ける
- **始まりと終わりがはっきりしている** — 説明を読めば、どこから手を付けてどこで終わりかが分かる

コードベースを調べ、変更するファイルや部品を具体的に書く（サブエージェントを起動できる環境では調査を任せる）。

サブタスクが8〜10件を超えるなら、課題とサブタスクではなく、エピックとストーリーに分けるべきかをユーザーに伝える。

### 各サブタスクに書くこと

各サブタスクの説明は、そのまま `spec` の入力に使える形にする:

```markdown
## 目的
<このサブタスクで何をするか>

## 範囲
- やること: ...
- やらないこと: ...（隣のサブタスクで扱うもの）

## 主に変えるファイル
- <path>

## 受け入れ条件
- <確かめられる形で>

## 依存
<先に終わっている必要があるサブタスク。無ければ「なし」>

親: <元の課題の URL>
```

## Step 4 — 分解案を見せて確認を取る

```markdown
# 分解案: <元の課題のタイトル>

元: <URL>　|　サブタスク: N件

| # | タイトル | 主に変えるもの | 依存 |
|---|---|---|---|
| 1 | <動詞で始まる要約> | <path> | — |
| 2 | ... | ... | 1 |

### 1. <タイトル>
<説明（上の形）>

### 2. ...

---
この内容で <GitHub のサブ issue | JIRA のサブタスク> を N件作成しますか？（まとめる・分ける・順番を変える・直すこともできます）
```

直してと言われたら直して再度見せる。文章で渡された場合は、ここで終わる（作成先が無いため）。
最後に「Issue にするなら作成先のリポジトリか JIRA のプロジェクトを教えてください」と1行添える。

## Step 5 — 作成する

依存の順に1件ずつ作る（番号が順番どおりになるように）。
作成前に、Step 1 で控えた既存のサブタスクに同じタイトルが無いか確かめ、あれば作らずにユーザーに確認する。

### GitHub

1. Issue を作る（本文はファイルに書いて `--body-file` で渡す。改行を正しく渡すため）:
   ```bash
   gh issue create --repo <owner/repo> --title "<タイトル>" --body-file <file>
   ```
   出力された URL を控える。元の課題のラベルやマイルストーンは引き継がない（ユーザーが求めた場合だけ付ける）。

2. 親のサブ issue として登録する:
   ```bash
   gh api graphql -f parent=<親の id> -f url=<作った Issue の URL> -f query='
   mutation($parent:ID!,$url:String!){
     addSubIssue(input:{issueId:$parent, subIssueUrl:$url}){ subIssue{ number } }
   }'
   ```
   親の `id` は Step 1 の `gh issue view --json id` で取ったもの（`I_` で始まる ID）。

3. 依存があれば「blocked by」を付ける（両方の Issue の `id` を `gh issue view <N> --json id` で取る）:
   ```bash
   gh api graphql -f issue=<後のサブタスクの id> -f blocking=<先のサブタスクの id> -f query='
   mutation($issue:ID!,$blocking:ID!){
     addBlockedBy(input:{issueId:$issue, blockingIssueId:$blocking}){ issue{ number } }
   }'
   ```

サブ issue や依存関係の登録が使えない場合（古い GitHub Enterprise など、mutation がエラーになる）は、
本文の「親:」「依存」の記述で関係を残し、作り終えた後に親の Issue へチェックリストのコメントを付ける
（本文はファイルに書いて `gh issue comment <N> --body-file <file>`）:

```markdown
## サブタスク
- [ ] #A <タイトル>
- [ ] #B <タイトル>
```

### JIRA

各サブタスクを `createJiraIssue` で作る:

- `cloudId`: 元の課題のサイト
- `projectKey`: 親と同じプロジェクト
- `issueType`: Step 1 で確認したサブタスクのタイプ名
- `parent`: 元の課題のキー
- `summary`: タイトル
- `description`: 説明（上の形）。`contentFormat: "markdown"`

依存関係は、Atlassian MCP の `executeWrite` で `createJiraIssueLink` を呼んで付ける:
`linkType: "Blocks"`、`inwardIssue`: 先のサブタスク（ブロックする側）、`outwardIssue`: 後のサブタスク（ブロックされる側）。
サイトで課題のリンクが無効になっていて失敗した場合は、説明の「依存」の記述だけで残す。

## Step 6 — 結果を伝える

```markdown
# 分解完了

元: <URL>　|　作成: N件

| # | 番号 / キー | タイトル | 依存 |
|---|---|---|---|
| 1 | #45 / PROJ-124 | ... | — |
| 2 | #46 / PROJ-125 | ... | #45 |

<作れなかったものがあれば、理由と一緒に>
```

最後に次の手を1行で示す: 「実装するなら、1件目から `spec <Issue の URL>` → `build`」。

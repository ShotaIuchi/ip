---
name: review-pr
description: >
  GitHub の PR を複数の専門家の観点でレビューし、指摘を PR の該当行へのコメントとして投稿するスキル。
  同じPRに以前このスキルでレビューしていれば再レビューになり、前回の指摘が直ったかを確認して
  （直ったスレッドは解決済みにし）、前回以降に追加されたコミットだけを新たにレビューする。
  --approve を付けると、Should 以上の指摘が無ければ承認（Approve）まで進める。
  「PRをレビューしてコメントして」「PRレビューを投稿」「再レビューして」「修正を確認して」
  「問題なければ承認して」等で起動する。チャットにレポートを出すだけなら review を使う。
argument-hint: "[<PR番号 | PR URL>] [--approve]"
---

# review-pr: PRをレビューして投稿する

PR をレビューし、指摘を該当行へのコメントとして投稿する。2回目以降は再レビューとして、前回の指摘の確認と新しい変更のレビューを行う。
`triage-pr`（PRのコメントを直して返信する）と対になっており、
`review-pr` → `triage-pr` → `review-pr`（再レビュー）の往復で回せる。

## 絶対に守ること

- **投稿・返信・スレッドの解決・承認の前に、必ず内容を見せてユーザーの確認を取る。** すべて外から見える操作である。
- 承認は `--approve` が付いている時だけ。付いていなければ、指摘が無くても承認しない。
- 変更されていない行の問題は指摘しない（差分だけがレビュー対象）。

## 重要度ガイド

`review` スキルと同じ定義を使う。

| 重要度 | 意味 | 対応 |
|---|---|---|
| **Must** | 直さないと壊れる・危ない（セキュリティホール、データ損失、クラッシュ、競合状態） | マージ前に必ず直す |
| **Should** | 直すべき（性能問題、設計負債、テスト不足、エラー処理の欠落） | 早めに直す |
| **Could** | 直してもよい（スタイル、軽微な改善） | 検討する |
| **Good** | 良い点 | 続ける |

## Step 1 — 対象のPRと前回のレビューを確認する

PRを特定する（番号・URLの指定、無ければ今のブランチのPR: `gh pr view --json number`）。

```bash
gh pr view <number> --json number,title,body,url,author,headRefOid,baseRefName,headRefName,isDraft
gh api user --jq .login   # 自分のlogin
```

- **自分のPRかどうか**: `author.login` が自分なら、承認も「修正を依頼」もできない（GitHubの仕様）。
  この場合レビューの種類は常に「コメント」になる。`--approve` が付いていたら、承認できない旨を最初に伝える。
- **前回のレビューがあるか**: 自分が投稿したレビューのうち、本文に `<!-- review-pr -->` を含むものを探す。

```bash
gh api repos/<owner>/<repo>/pulls/<number>/reviews --paginate \
  --jq '[.[] | select(.user.login=="<me>" and (.body|contains("<!-- review-pr -->")))] | last | {id, commit_id, submitted_at}'
```

見つかれば（`id` が null でなければ）**再レビュー（Step 3）**、無ければ **初回レビュー（Step 2）**。

前回レビューしたコミット（`commit_id`）がローカルに無ければ取得する:

```bash
git fetch origin "pull/<number>/head"
git cat-file -e <commit_id> 2>/dev/null || echo "前回のコミットが見つからない"
```

force push などで前回のコミットが見つからない場合は、前回の指摘の確認だけ行い、新しい変更のレビューは PR 全体を対象にする（その旨をまとめに書く）。

## Step 2 — 初回レビュー

PRの差分（`gh pr diff <number>`）を、PRのタイトル・本文・リンクされた Issue を文脈にしてレビューする。
手順は `review` スキルと同じ:

1. 関係する観点を選ぶ — 正確性 / テスト / セキュリティ / パフォーマンス / 設計・保守性 / 並行性・状態 / 信頼性 /
   最新動向（Web検索が使える場合のみ）。無関係な観点は使わない。
   正確性は、`code-review` スキル（Claude Code 標準）が使える場合はそちらに PR 番号を渡して任せる
   （`--comment` は渡さない。投稿はこのスキルがまとめて行う）。重要度の読み替えは `review` スキルと同じ
   （important → Should、致命的なら Must ／ nit → Could ／ pre_existing → まとめコメントに参考として1行）。
2. サブエージェントを起動できる環境では観点ごとに並列に、できなければ1観点ずつ順にレビューする。
   各観点には差分（対象）と変更ファイル全体（参照用の文脈）を区別して渡し、
   `{severity, title, location(path:line), detail, recommendation}` の形で指摘を返させる。
3. 指摘を統合する — 重要度順に並べ、同じ問題を複数観点が指摘していれば1件にまとめる。

続けて Step 4 へ。

## Step 3 — 再レビュー

### 3-1. 前回の指摘が直ったか確認する

前回のレビューで付けたスレッドを取得する（自分のコメントで始まり `<!-- review-pr -->` を含むスレッド）:

```bash
gh api graphql -f owner=<owner> -f repo=<repo> -F num=<number> -f query='
query($owner:String!,$repo:String!,$num:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$num){
      reviewThreads(first:100){
        nodes{
          id isResolved isOutdated path line
          comments(first:50){ nodes{ databaseId author{login} body url } }
        }
      }
    }
  }
}'
```

解決済みでない各スレッドについて、指摘の内容と、前回のコミットから今の HEAD までの変更
（`git diff <commit_id>..<headRefOid> -- <path>`）、スレッド内の返信（`triage-pr` の「`<sha>` で修正」など）を突き合わせて判定する:

| 判定 | 意味 | 投稿すること |
|---|---|---|
| 直った | 指摘が解消されている | 「確認しました」と返信し、スレッドを解決済みにする |
| 一部だけ | 解消が不十分 | 何が足りないかを返信する（解決しない） |
| 直っていない | 変化なし、または別の形で残っている | 残っている理由を返信する（解決しない） |

コードを読んで確認すること。返信に「直した」と書かれているだけで直ったと判定しない。

### 3-2. 新しい変更だけをレビューする

前回のコミットから今の HEAD までの差分（`git diff <commit_id>..<headRefOid>`）だけを、Step 2 と同じ手順でレビューする。
修正によって新たに入った問題を探すのが目的で、PR全体をレビューし直すことはしない。

続けて Step 4 へ。

## Step 4 — レビューの種類を決める

| 条件 | レビューの種類 |
|---|---|
| 自分のPR | コメント（COMMENT） |
| `--approve` 無し | コメント（COMMENT） |
| `--approve` 有り、かつ **Must・Should の指摘が残っていない**（初回: Must/Should が0件。再レビュー: 前回の指摘が全て「直った」で、新しい Must/Should も0件） | **承認（APPROVE）**。Could はコメントとして一緒に付ける |
| `--approve` 有り、かつ Must・Should の指摘が残っている | **修正を依頼（REQUEST_CHANGES）** |

## Step 5 — 投稿内容を見せて確認を取る

投稿する前に、全部をまとめて見せる:

```
PR #123 に次の内容でレビューを投稿します（種類: 承認 | 修正を依頼 | コメント）

[前回の指摘の確認]（再レビューの場合）
  ✓ 直った 3件 → 返信して解決済みにする
  △ 一部だけ 1件 → 返信のみ
  ✗ 直っていない 0件

[新しい指摘] 4件
  1. [Must] path:line — タイトル
  2. [Should] path:line — タイトル
  3. [Could] path:line — タイトル
  4. [Could] （行に紐づかない）— タイトル → まとめコメントに入れる

[まとめコメント]
  <下のテンプレートの内容>

投稿しますか？（外したい指摘があれば番号で指定）
```

ユーザーが指摘を外したら、Step 4 の判定をやり直す（外した結果 Must・Should が0件になれば承認になりうる）。
その場合は種類が変わったことを明示して、もう一度確認する。

## Step 6 — 投稿する

### 行コメント付きのレビューを投稿する

指摘のうち、差分に含まれる行を指すものは行コメントにする。差分外の行や場所の無い指摘はまとめコメント（本文）に入れる。
JSON をファイルに書いてから投稿する:

```json
{
  "commit_id": "<headRefOid>",
  "event": "APPROVE | REQUEST_CHANGES | COMMENT",
  "body": "<まとめコメント>\n\n<!-- review-pr -->",
  "comments": [
    {
      "path": "src/auth.ts",
      "line": 42,
      "side": "RIGHT",
      "body": "**[Must] SQLインジェクション**\n\n<詳細>\n\n**提案:** <修正案>\n\n<!-- review-pr -->"
    }
  ]
}
```

```bash
gh api repos/<owner>/<repo>/pulls/<number>/reviews -X POST --input <file.json>
```

行の指定が差分外だとエラーになる。その指摘はまとめコメントに移して投稿し直す。

まとめコメントのテンプレート:

```markdown
## レビュー結果（<初回 | 再レビュー>）

| Must | Should | Could |
|---|---|---|
| N | N | N |

<再レビューの場合>
**前回の指摘**: <N>件中 <M>件が直っていることを確認しました。
<一部だけ・直っていない ものがあれば1行ずつ>

<行に紐づかない指摘があればここに>

<Good があれば1〜3行>
```

### 前回の指摘への返信とスレッドの解決（再レビューの場合）

各スレッドに返信する:

```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments/<最初のコメントのdatabaseId>/replies \
  -f body="<確認結果>
<!-- review-pr -->"
```

「直った」スレッドだけ解決済みにする:

```bash
gh api graphql -f id=<thread id> -f query='mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ isResolved } } }'
```

## Step 7 — 結果を伝える

投稿したレビューのURL、レビューの種類、件数を伝える。
修正を依頼した場合は「直すなら `triage-pr`」と1行添える。
自分のPRで `--approve` が付いていた場合は、承認できなかったことをもう一度伝える。

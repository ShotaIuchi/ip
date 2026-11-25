# GitHub Issues（gh）

GitHub（github.com と GitHub Enterprise）の Issue を `gh` で操作する。ここにはツールの違いだけを書く。
できない操作・断られた操作をどうするかは `issue` の SKILL.md に従う。

## 共通

- **接続**: `gh` のログインを使う。`gh auth status --hostname '<host>'` で確かめ、`gh` が無い・ログインしていなければ、
  `gh` を入れて `gh auth login --hostname '<host>'` でログインするよう伝えて止まる。
- **ホスト**: 接続先（番号だけのときの決め方は `issue` の SKILL.md の Step 2。ホストの省略時は `github.com`）のホストを、すべてのコマンドに渡す。
  `gh issue`・`gh label` は `--repo '<host>/<owner>/<repo>'`、`gh api` は `--hostname '<host>'`、`gh project` は環境変数 `GH_HOST='<host>'`。
- **値の渡し方**: 値は単一引用符で囲んで渡し（中の `'` は `'\''`）、本文は一時ファイルに書いて `--body-file` で渡す。
  GraphQL の操作には Issue の番号ではなく ID が要る（`gh issue view <N> --repo '<host>/<owner>/<repo>' --json id`）。
- **状態**: Issue は open / closed だけである。それ以外の状態は、運用ファイルで決めたラベル（または Projects のフィールド）で表す。
- **断られたことの見分け方**: 古い GitHub Enterprise などで機能が無いと、GraphQL が `Field '<名前>' doesn't exist on type ...` を返す。
  その機能は**できない**。

## 探す

```bash
gh issue list --repo '<host>/<owner>/<repo>' --state <open | closed | all> --json number,title,url,labels,assignees,state --limit 50
```
頼みに合わせて `--assignee @me`、`--label '<ラベル>'`、`--search '<言葉>'` を足す。

## 見る

```bash
gh issue view <N> --repo '<host>/<owner>/<repo>' --json id,number,title,body,url,state,stateReason,labels,assignees,milestone,comments
```
子と依存は GraphQL で取る。片方だけ無い GitHub もあるので、別々に問い合わせる。
```bash
gh api graphql --hostname '<host>' -f owner='<owner>' -f repo='<repo>' -F n=<N> -f query='
query($owner:String!,$repo:String!,$n:Int!){
  repository(owner:$owner,name:$repo){ issue(number:$n){ subIssues(first:100){ nodes{ number title url state } } } } }'
gh api graphql --hostname '<host>' -f owner='<owner>' -f repo='<repo>' -F n=<N> -f query='
query($owner:String!,$repo:String!,$n:Int!){
  repository(owner:$owner,name:$repo){ issue(number:$n){ blockedBy(first:100){ nodes{ number title url state } } } } }'
```

## 作る

```bash
gh issue create --repo '<host>/<owner>/<repo>' --title '<タイトル>' --body-file '<file>' --label '<ラベル>' --assignee '<ログイン名>'
```
要る引数だけを付ける。出力された URL を控える。

## 子を作る

「作る」で Issue を作り、親のサブ issue として登録する。親の既にある子は「見る」の `subIssues` で取る。
```bash
gh api graphql --hostname '<host>' -f parent='<親の id>' -f url='<作った Issue の URL>' -f query='
mutation($parent:ID!,$url:String!){ addSubIssue(input:{issueId:$parent, subIssueUrl:$url}){ subIssue{ number } } }'
```
GitHub の Issue に決まった種類は無い。子の種類は運用ファイルに決まりがあれば（ラベル・Issue の種類）それに従う。

## 更新

```bash
gh issue edit <N> --repo '<host>/<owner>/<repo>' --title '<タイトル>' --body-file '<file>' --add-label '<ラベル>' --remove-label '<ラベル>' --add-assignee '<ログイン名>'
```
要る引数だけを付ける。本文を書き換えるときは、今の本文を「見る」で取り、変えない部分を残す。

## 状態を進める

運用ファイルの「状態の流れ」で、今と目的の状態の表し方を確かめ、違うところをすべて変える（状態のラベルの付け替え、閉じる・開き直す、フィールド）。
```bash
gh issue edit <N> --repo '<host>/<owner>/<repo>' --remove-label '<今の状態のラベル>' --add-label '<新しい状態のラベル>'
gh issue close <N> --repo '<host>/<owner>/<repo>' --reason '<completed | not planned>'
gh issue reopen <N> --repo '<host>/<owner>/<repo>'
```
Projects のフィールドで表すときは、`project` の権限が要る（`gh auth refresh --hostname '<host>' -s project`）。
`GH_HOST='<host>' gh project` の `field-list`・`item-list` で ID を取り、`item-edit` で書き換える（Issue が入っていなければ `item-add`）。

## コメント

```bash
gh issue comment <N> --repo '<host>/<owner>/<repo>' --body-file '<file>'
```

## 依存を付ける

「blocked by」を付ける（両方の Issue の ID が要る）。
```bash
gh api graphql --hostname '<host>' -f issue='<後の Issue の id>' -f blocking='<先の Issue の id>' -f query='
mutation($issue:ID!,$blocking:ID!){ addBlockedBy(input:{issueId:$issue, blockingIssueId:$blocking}){ issue{ number } } }'
```

## 工数を記録する

**できない。** GitHub の Issue には工数（見積もり・実績）の機能が無い。

## 運用を集める

読み取りだけで集める（`setup` が使う）。

- ラベル: `gh label list --repo '<host>/<owner>/<repo>' --limit 200 --json name,description,color`
- Issue テンプレート: `.github/ISSUE_TEMPLATE/`・`.github/ISSUE_TEMPLATE.md` など GitHub が読む場所を `gh api 'repos/<owner>/<repo>/contents/<パス>' --hostname '<host>'` で読む
- 直近の Issue の使われ方: `gh issue list --repo '<host>/<owner>/<repo>' --state all --limit 50 --json number,title,labels,state,stateReason,body`
  （状態らしいラベル・種類らしいラベル・タイトルの付け方・本文の見出し）
- Projects を使っていれば: `GH_HOST='<host>' gh project list --owner '<owner>' --format json` と `field-list`（状態のフィールド）

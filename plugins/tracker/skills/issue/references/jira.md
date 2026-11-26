# Jira（Atlassian MCP）

Jira の課題を Atlassian MCP のツールで操作する。ここにはツールの違いだけを書く。
できない操作・断られた操作をどうするかは `issue` の SKILL.md に従う。`tracker:view` も「探す」「見る」「ライブ」を使う。

## 共通

- **接続**: Atlassian MCP の接続を使う。そのツール（`getJiraIssue` など）が無い・認証が切れている環境では、Jira を扱えないことと、
  その環境に Atlassian MCP を設定する方法（Claude Code なら `/mcp`）を伝えて止まる。
- **サイト**: 運用ファイルの接続先のサイトを `cloudId` に渡す。分からなければ `getAccessibleAtlassianResources` で一覧を取り、
  1つならそれを使って示し、複数なら聞く。
- **操作の呼び方**: 下の主な操作はそのまま呼ぶ。「`executeRead` の 〜」「`executeWrite` の 〜」と書いたものは、
  そのツールに操作の名前を渡して呼ぶ（`cloudId` は `inputs` の外）。ここに無い操作だけ `discover` で探す。
  見つからない・断られたら `discover` で確かめ直す。
- **値の渡し方**: 本文は `contentFormat: "markdown"` で渡す（HTML で取れた本文を書き戻すなら `"html"`）。
  JQL に入れる値は、キーは形を確かめ、言葉は引用符を逃がしてから入れる。カスタムフィールドは `additional_fields` で渡す。
- **断られたことの見分け方**: 機能が無効（課題のリンク・時間管理など）というエラーが返る、または `discover` で操作が見つからない。
  その操作は**できない**。

## 探す

`searchJiraIssuesUsingJql`（`jql`、`maxResults`）。運用ファイルのプロジェクトに絞る（`project = <KEY>`）。
例: 自分の担当は `assignee = currentUser() AND statusCategory != Done`（運用ファイルの状態の流れがあれば、その終わりの状態で絞る）、今のスプリントは `sprint in openSprints()`、言葉は `text ~ "<言葉>"`。
1回で返るのは `maxResults`（既定50・上限100）件までである。全部を取るときは、応答にある次のページの印を次の呼び出しに渡し、`isLast` が真になるまで続きを取る（印の引数の名前はツールの定義で確かめる）。
一覧の項目を決めて取るときは `view: "full"` と `fields`（`summary`、`status`、`assignee`、`issuetype`、`labels`、`updated`）を渡す。
共通の項目（`tracker:view`）: キー ← `key`、タイトル ← `summary`、状態 ← `status`、担当 ← `assignee`、種類 ← `issuetype`、ラベル ← `labels`、更新日 ← `updated`、URL ← `key`（`https://<site>.atlassian.net/browse/<キー>`）。

## 見る

`getJiraIssue`（`issueIdOrKey`、`view: "evidence"`）。子課題（`subtasks`）と課題のリンクも返る。
エピックの下の課題は `subtasks` に入らないので、`searchJiraIssuesUsingJql` の `parent = <KEY>` で取る。
コメントは `listJiraIssueComments`。編集の準備には `includeEditableFields: true` で、編集できる項目と選べる値を取る。
共通の項目（`tracker:view`）: `view: "evidence"` で `key`・`summary`・`status`・`assignee`・`issuetype`・`labels`・`updated` も返る。当て方は「探す」と同じ。

## 作る

`createJiraIssue`（`projectKey`、`issueType`、`summary`、`description`、`labels`、`assignee`、ほかの必須項目は `additional_fields`）。
`issueType` は運用ファイルの種類の名前。無ければ `executeRead` の `listJiraProjectIssueTypesMetadata`（`projectIdOrKey`）から選ぶ。
失敗すると、足りない項目と選べる値が返る。それを結果として返す。

## 子を作る

`createJiraIssue` に `parent`（親のキー）を付けて作る。子の種類は運用ファイルに決まりが無ければ、
`listJiraProjectIssueTypesMetadata` で決める（通常の課題の子は `subtask` が真の種類、エピックの子は通常の課題の種類）。
サブタスクは子を持てないので、サブタスクの子は**できない**。

## 更新

`editJiraIssue`（`issueIdOrKey`、`fields`、`additional_fields`）。
`labels` などの複数の値の項目は置き換えになるので、今の値を「見る」で取って足した全体を渡す。状態はここでは変えない。

## 状態を進める

その課題で今使える遷移の一覧を `executeRead` の `listJiraIssueTransitions`（`issueIdOrKey`）で取り、行き先の状態が目的の状態の遷移を選んで、
`transitionJiraIssue`（`issueIdOrKey`、`transitionId`、遷移で必須の項目は `fields`）で進める。
行き先が目的の状態の遷移が無ければ、その状態へは**できない**（今の状態と使える遷移を添える）。

## コメント

`addOrEditJiraIssueComment`（`issueIdOrKey`、`commentBody`、`contentFormat: "markdown"`）。

## 依存を付ける

課題のリンクで付ける。`executeWrite` の `createJiraIssueLink`（`linkType: "Blocks"`、`inwardIssue`: 先の課題、`outwardIssue`: 後の課題）。
リンクの種類の名前はサイトで違うことがあるので、運用ファイルに決まりがあればそれに従う。

## 工数を記録する

- 実績（作業ログ）: `discover` で作業ログを足す操作を探し、`executeWrite` で呼ぶ。
- 見積もり: 運用ファイルの「工数」で決めた項目を `editJiraIssue` で書く。

## 運用を集める

読み取りだけで集める（`setup` が使う）。

- 課題の種類（サブタスクの種類も）: `executeRead` の `listJiraProjectIssueTypesMetadata`
- ワークフローの状態と遷移: `executeRead` の `listJiraStatuses`（状態の一覧）と、直近の課題での `listJiraIssueTransitions`
- 種類ごとの必須項目: `executeRead` の `getJiraIssueTypeMetaWithFields`（プロジェクトと課題の種類ごと）
- 直近の課題の使われ方: `searchJiraIssuesUsingJql`（`project = <KEY> ORDER BY updated DESC`、`view: "evidence"`）。
  ラベル・コンポーネント・優先度・見積もりの項目・作業ログの有無・説明の見出し

## ライブ

`tracker:view` のページ（フォーマットの更新が `開いたとき`・`<N>秒`）が、見る人自身の接続で自動で取り直すときに使う。

- **コネクタ**: claude.ai の Atlassian のコネクタ（ページの `mcp` 機能で宣言する `server` は、そのコネクタの表示名）。
- **ツール**: 「探す」「見る」に当たる読み取りのツールだけを宣言する。一覧（とエピックの下の課題）は `searchJiraIssuesUsingJql`、
  1件の本文・子課題は `getJiraIssue`、コメントは `listJiraIssueComments`。入力は「探す」「見る」と同じ。
- **JQL**: ビューの条件のうち JQL に直せるものは JQL に入れ、「共通」の値の渡し方で組む。運用ファイルのプロジェクトへの絞り込み（`project = <KEY>`）を必ず付ける。
- 引数の名前と結果の形は、そのセッションのツールの定義と、1回の実際の呼び出し（読み取り）で確かめる。

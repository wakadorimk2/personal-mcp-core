# issue-create

**種類**: create
**正本**: このファイル（`docs/skills/issue-create.md`）
**Claude用アダプタ**: `.claude/skills/issue-create/SKILL.md`
**Codex用アダプタ**: `.codex/skills/issue-create/SKILL.md`

---

## Mission

`issue-draft` で確定した title/body・ラベル候補・repo情報を受け取り、
`gh` コマンドで GitHub Issue を作成するための手順を標準化する。
ラベル存在確認・重複チェックを必須とし、作成後の URL/番号記録を義務付ける。
さらに Projects / relationship などのメタデータを可能な限り埋める。

---

## 前提条件（必須）

- **`issue-draft` が完了していること** — 確定済み title/body（DRAFTラベル除去済み）が人間に承認済みであること
- **repo情報が確定していること** — `owner` と `repo` が明示されていること
- issue-draft 未完了のまま create を実行してはならない

---

## Dependencies

- blocked by #104（`gh label list` 出力形式の確定待ち）

---

## Blockers

- #104 未マージ: ラベル存在確認コマンドの出力形式が確定していないため、ラベル照合手順が固まらない

---

## Rules（絶対）

1. **`gh label list` によるラベル存在確認を必須とする** — ラベル候補を適用する前に必ずリポジトリ上のラベル一覧を取得し、存在しないラベルは適用しない
2. **重複疑い時は `gh issue list --search` を実行してから作成判断する** — タイトルや Goal に類似 Issue が存在する可能性がある場合は検索を先行させる
3. **作成後の URL/番号記録を必須とする** — `gh issue create` の出力から URL と番号を取得し、必ず記録・出力する
4. **再実行可能なコマンド形式を維持する** — 同じ入力から同じコマンドが生成できる形式にする（body はファイル経由 `--body-file` を推奨）
5. **実際のコマンド実行はしない** — コピペ可能なコマンド案を生成するのみ（実行は Codex 側）
6. **メタデータは可能な限り反映する** — Projects / relationship（blocked-by / sub-issue など）の入力がある場合は、Issue 作成後に反映用コマンドを必ず出力する

---

## Inputs

| 項目 | 必須 | 説明 |
|---|---|---|
| `title` | 必須 | `issue-draft` Output B の確定タイトル（50字以内） |
| `body` | 必須 | `issue-draft` Output A の確定 Markdown（DRAFTコメント除去済み） |
| `labels` | 任意 | 適用候補ラベル名のリスト（例: `["bug", "enhancement"]`） |
| `owner` | 必須 | GitHub リポジトリオーナー名（例: `wakadorimk2`） |
| `repo` | 必須 | GitHub リポジトリ名（例: `personal-mcp-core`） |
| `projects` | 任意 | 追加先 Project の識別子リスト（Project 番号や ID） |
| `blocked_by` | 任意 | 依存元 Issue 番号のリスト（この Issue が block される側） |
| `sub_issues` | 任意 | 子 Issue の番号リスト（親子関係を付ける場合） |

---

## Procedure（作業手順）

1. **前提確認** — `issue-draft` 完了・DRAFT除去済み・owner/repo 確定を確認する
2. **ラベル存在確認（必須）** — `gh label list` コマンドを生成し、候補ラベルの照合手順を示す
3. **重複チェック（疑いがある場合）** — タイトル類似度が高い場合は `gh issue list --search` コマンドを生成し、結果確認を求める
4. **`gh issue create` コマンドを生成する**（Output A）
5. **メタデータ反映コマンドを生成する**（Output B）
6. **作成後の記録手順を示す**（Output C）

---

## Output A: コピペ可能な gh コマンド

> 以下のコマンドをそのまま実行できる形式で提示する。
> **実行は Codex または人間が行う。Claude はコマンドを実行しない。**

### ステップ 1: ラベル存在確認（必須）

```bash
# ラベル名を1行1件で取得し、厳密一致で存在確認する（例: "bug" を確認）
gh label list --repo <owner>/<repo> --json name --jq '.[].name' | grep -xF "bug"

# 複数ラベルをまとめて確認する場合
gh label list --repo <owner>/<repo> --json name --jq '.[].name' > /tmp/repo-labels.txt
grep -xF "label1" /tmp/repo-labels.txt
grep -xF "label2" /tmp/repo-labels.txt
```

> `grep -xF` は行全体の完全一致（`-x`）・固定文字列（`-F`）で照合するため、
> 部分一致による誤検知（例: "bug" が "debug" にマッチする）を防ぐ。
>
> **注意（#104 依存）**: `gh label list --json` の出力フィールド名は #104 で確定予定。
> 現時点では `name` を想定しているが、#104 マージ後に実際の出力形式と照合すること。
> 確定前は `gh label list --repo <owner>/<repo>` で全件取得し目視確認を代替手段とする。
>
> ラベルが存在しない場合は適用しない。存在しないラベルを `--label` に渡すとエラーになる。

### ステップ 2: 重複チェック（疑いがある場合）

```bash
# タイトルのキーワードで既存 Issue を検索する
gh issue list --repo <owner>/<repo> --search "<title-keyword>" --state all
```

> 類似 Issue が見つかった場合は、重複か否かを人間が判断してから作成に進む。

### ステップ 3: Issue 作成

```bash
# body をファイルに保存してから実行する（再実行可能形式）
cat > /tmp/issue-body.md << 'EOF'
<issue-draft Output A の Markdown をここに貼る>
EOF

gh issue create \
  --repo <owner>/<repo> \
  --title "<title>" \
  --body-file /tmp/issue-body.md \
  --label "<label1>" \
  --label "<label2>"
```

> ラベルなしの場合は `--label` 行を省く。

---

## Output B: メタデータ反映コマンド（任意だが推奨）

> Projects / relationship の入力がある場合は、以下をそのまま実行できる形式で提示する。
> 対象入力がない項目は省略してよい。

### B-1: Project 追加

```bash
# 例: 作成済み Issue #<number> を Project に追加する
gh issue edit <number> \
  --repo <owner>/<repo> \
  --add-project "<project>"
```

### B-2: relationship 追加（blocked by）

```bash
# 例: Issue #<number> が Issue #<blocked_by_number> に block される関係を追加
printf '{"issue_id":<blocked_by_issue_id>}' > /tmp/blocked-by.json
gh api -X POST \
  repos/<owner>/<repo>/issues/<number>/dependencies/blocked_by \
  --input /tmp/blocked-by.json
```

### B-3: relationship 追加（sub-issue）

```bash
# 例: Issue #<sub_issue_number> を Issue #<number> の sub-issue として追加
printf '{"sub_issue_id":<sub_issue_number>}' > /tmp/sub-issue.json
gh api -X POST \
  repos/<owner>/<repo>/issues/<number>/sub_issues \
  --input /tmp/sub-issue.json
```

> 注意:
> - relationship API の利用可否・payload は GitHub 側仕様/権限に依存する。実行前に利用可能性を確認すること。
> - Issue 番号しかない場合、`<blocked_by_issue_id>` への解決手順（GraphQL / API 参照）は別途運用ルールに従う。

---

## Output C: 作成結果の記録フォーマット

> `gh issue create` 実行後、以下の形式で結果を記録・出力する（必須）。

```text
## Issue 作成結果

- **URL**: https://github.com/<owner>/<repo>/issues/<number>
- **番号**: #<number>
- **title**: <title>
- **labels**: <適用されたラベル一覧（なければ「なし」）>
- **projects**: <追加した Project 一覧（なければ「なし」）>
- **relationship**: <追加した関係（blocked_by/sub_issue など。なければ「なし」）>
- **作成日時**: <YYYY-MM-DD HH:MM>
```

---

## 成功例

### 入力

- title: `add issue-create skill spec`
- labels候補: `["documentation", "enhancement"]`
- owner/repo: `wakadorimk2/personal-mcp-core`

### 生成されるコマンド（ステップ順）

```bash
# 1. ラベル存在確認（厳密一致）
gh label list --repo wakadorimk2/personal-mcp-core --json name --jq '.[].name' | grep -xF "documentation"
gh label list --repo wakadorimk2/personal-mcp-core --json name --jq '.[].name' | grep -xF "enhancement"

# 2. 重複チェック（"issue-create" でキーワード検索）
gh issue list --repo wakadorimk2/personal-mcp-core --search "issue-create" --state all

# 3. Issue 作成
gh issue create \
  --repo wakadorimk2/personal-mcp-core \
  --title "add issue-create skill spec" \
  --body-file /tmp/issue-body.md \
  --label "documentation" \
  --label "enhancement"

# 4. メタデータ反映（例）
gh issue edit <created-issue-number> \
  --repo wakadorimk2/personal-mcp-core \
  --add-project "Team Board"

printf '{"sub_issue_id":103}' > /tmp/sub-issue.json
gh api -X POST \
  repos/wakadorimk2/personal-mcp-core/issues/<created-issue-number>/sub_issues \
  --input /tmp/sub-issue.json
```

### 作成結果記録（例）

```text
## Issue 作成結果

- **URL**: https://github.com/wakadorimk2/personal-mcp-core/issues/105
- **番号**: #105
- **title**: add issue-create skill spec
- **labels**: documentation, enhancement
- **projects**: Team Board
- **relationship**: sub_issue #103
- **作成日時**: 2026-03-05 10:00
```

---

## 失敗例（ダメ例）

### ダメ例 1: ラベル確認を曖昧一致で行う

```bash
# NG: grep -w や grep -E は部分一致するため誤検知が起きる
gh label list --repo <owner>/<repo> | grep -w "bug"
# → "debug" や "bug-fix" などがヒットし、"bug" が存在すると誤判定する可能性がある

gh label list --repo <owner>/<repo> | grep -E "documentation|enhancement"
# → "documentation-draft" が "documentation" にマッチしてしまう
```

**修正**: `--json name --jq '.[].name'` でラベル名のみ取り出し、`grep -xF` で完全一致照合する。

### ダメ例 3: ラベル確認なしで `--label` を渡す

```bash
# NG: ラベルが存在するか確認せずに使用している
gh issue create --title "add issue-create" --label "new-feature"
# → "new-feature" がリポジトリに存在しない場合エラーになる
```

**修正**: 必ず `gh label list --json name --jq '.[].name' | grep -xF` でラベルの存在を確認してから `--label` に渡す。

### ダメ例 4: 重複チェックをスキップして作成する

```bash
# NG: 類似タイトルの Issue が存在するか確認せず作成している
gh issue create --title "issue-create skill"
# → 既存の Issue #103 と重複する可能性がある
```

**修正**: タイトルキーワードで `gh issue list --search` を先に実行し、人間が重複でないと判断してから作成する。

### ダメ例 5: 作成後の URL/番号を記録しない

```bash
# NG: 実行して終わり — URL/番号を出力・記録していない
gh issue create --title "..." --body-file body.md
```

**修正**: 実行後に Output B のフォーマットで URL と番号を必ず記録・出力する。

### ダメ例 6: body をインラインで渡す

```bash
# NG: --body に直接 Markdown を埋め込んでいる（再実行困難・エスケープ問題あり）
gh issue create --title "..." --body "## Goal\n..."
```

**修正**: body は必ずファイルに保存して `--body-file` で渡す。

---

## 前提未充足時の対応

| 状況 | 対応 |
|---|---|
| issue-draft 未完了 | create を拒否し、`/issue-draft` を先に完了するよう伝える |
| DRAFT コメントが残存 | DRAFT 除去を求め、人間の確認を促す |
| owner/repo が未指定 | 必須情報として owner と repo の入力を求める |
| ラベル候補が存在しない | そのラベルを外したコマンドを生成し、ラベルなし作成を提案する |
| 重複 Issue が見つかった | 重複候補の URL/番号を列挙し、人間に作成可否を確認する |
| Projects / relationship の入力が不足 | Issue は作成し、記録フォーマットに `なし` を明記して追記TODOを残す |

---

## 禁止

- issue-draft 未完了のまま create コマンドを生成する
- `gh label list` を省略してラベルを適用する
- 重複チェックの結果を無視して作成を強行する
- 作成後の URL/番号記録を省略する
- `gh issue create` を Claude 自身が実行する
- body を `--body` フラグに直接インライン記述する
- Projects / relationship の入力があるのに反映コマンドを省略する

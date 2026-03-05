# issue-project-meta

**種類**: post-create
**正本**: このファイル（`docs/skills/issue-project-meta.md`）
**Claude用アダプタ**: `.claude/skills/issue-project-meta/SKILL.md`
**Codex用アダプタ**: `.codex/skills/issue-project-meta/SKILL.md`

---

## Mission

Issue 作成後に、Projects の列・優先度・依存関係を一貫した手順で反映する。
Project 側の設定値と Issue 本文の依存記述を一致させ、記録テンプレートを残す。

---

## Dependencies

- blocked by #105

---

## 前提条件（必須）

- **`gh issue create` が完了し、Issue URL / 番号が確定していること** — 作成前に本 skill を実行しない
- **`issue-create` Output B（引き渡し情報）が手元にあること** — `issue_url`・`issue_number`・`owner`・`repo`・`project_number` を確認する
- **対象 Project が存在していること** — 未作成の Project への追加は本 skill の範囲外

> 上記が未充足の場合は、未充足理由を記録して終了する（実行を強行しない）。

---

## Rules（絶対）

1. **Issue 作成後にのみ実施する** — `gh issue create` より前に Project メタ更新を行わない
2. **列 / 優先度の根拠を記録する** — なぜその値にしたかを 1 行で残す
3. **依存関係は Issue 本文と Project 側を整合させる** — 乖離がある場合は更新対象を明記してそろえる
4. **実行不能時は未実施理由を残す** — TODO と理由を記録し、未完了を隠さない
5. **コマンドは再実行可能形式で提示する** — プレースホルダを明示し、コピペ可能な形で出力する

---

## Inputs

| 項目 | 必須 | 説明 |
|---|---|---|
| `issue_url` | 必須 | 作成済み Issue URL |
| `issue_number` | 必須 | 作成済み Issue 番号（例: `106`） |
| `owner` | 必須 | GitHub オーナー |
| `repo` | 必須 | GitHub リポジトリ |
| `project_number` | 必須 | 対象 Project 番号 |
| `project_id` | 任意 | 対象 Project ID（未取得なら手順内で取得） |
| `item_id` | 任意 | Project に追加済み item の ID（未取得なら追加後に取得） |
| `status_field_id` | 任意 | Status フィールド ID |
| `status_option_id` | 任意 | 設定する Status オプション ID |
| `priority_field_id` | 任意 | Priority フィールド ID |
| `priority_option_id` | 任意 | 設定する Priority オプション ID |
| `blocked_by_issue_id` | 任意 | blocked-by 先の GraphQL issue_id |
| `sub_issue_number` | 任意 | sub-issue として追加する Issue 番号 |

---

## Procedure（作業手順）

1. Issue が作成済みであることを確認する
2. 必要な ID を取得する（`project_id`・`item_id`・`field_id`・`option_id`）
3. Project へ item を追加する
4. Status / Priority を必要に応じて更新する
5. blocked-by / sub-issue 関係を必要に応じて追加する
6. 反映結果と根拠を Output B テンプレートで記録する

---

## Output A: コピペ可能な反映コマンド

```bash
# --- 0) 必要な ID を取得する（未取得の場合のみ実行）---

# project_id 取得
gh project list --owner <owner> --format json \
  --jq '.projects[] | select(.number == <project-number>) | .id'

# item_id 取得（Project に Issue を追加した後で実行）
gh project item-list <project-number> --owner <owner> --format json \
  --jq '.items[] | select(.content.number == <issue-number>) | .id'

# Status / Priority フィールド一覧取得（field_id と option_id を確認）
gh project field-list <project-number> --owner <owner> --format json
# → 出力から "Status" / "Priority" の id と options[].id を読み取る

# 1) Project に Issue を追加
gh project item-add <project-number> --owner <owner> --url <issue-url>

# 2) Status 更新（任意）
gh project item-edit --id <item-id> --project-id <project-id> --field-id <status-field-id> --single-select-option-id <status-option-id>

# 3) Priority 更新（任意）
gh project item-edit --id <item-id> --project-id <project-id> --field-id <priority-field-id> --single-select-option-id <priority-option-id>

# 4) blocked-by 追加（任意）
printf '{"issue_id":<blocked_by_issue_id>}' > /tmp/blocked-by.json
gh api -X POST repos/<owner>/<repo>/issues/<issue-number>/dependencies/blocked_by --input /tmp/blocked-by.json

# 5) sub-issue 追加（任意）
printf '{"sub_issue_id":<sub_issue_number>}' > /tmp/sub-issue.json
gh api -X POST repos/<owner>/<repo>/issues/<issue-number>/sub_issues --input /tmp/sub-issue.json
```

> **注意（sub-issues / blocked-by API）**: 上記エンドポイントは GitHub の Sub-issues 機能に依存する。
> ベータ・プレビュー段階では形式が変わる場合があるため、実行前に公式ドキュメントと照合すること。
> 実行できない場合は Output B の TODO 欄に記録して終了する。

---

## Output B: 反映記録テンプレート

```md
- Project: <project-name>
- Status: <status-value>
- Priority: <priority-value>
- Dependencies: blocked by #<number> / sub-issue #<number>
- Rationale: <列/優先度の根拠を1行>
- Result: <done | partial | todo>
- TODO: <未実施があれば記載。なければ「なし」>
```

---

## 失敗時の扱い

- 権限不足・ID 未解決で実行できない場合は、未実施項目を TODO として残す
- 依存関係が本文と不一致の場合は、どちらを正としたかを明記する

---

## 前提未充足時の対応

| 状況 | 対応 |
|---|---|
| Issue 未作成（番号が確定していない） | 実行を中断し、`issue-create` を先に完了するよう伝える |
| `project_number` が未指定 | Project 追加・メタ更新をスキップし、TODO として記録する |
| フィールド ID / オプション ID が取得できない | `gh project field-list` を再実行して手動確認を求める |
| blocked-by API が利用不可 | Issue 本文の `## Dependencies` 欄を手動更新し、TODO に記録する |
| sub-issue API が利用不可 | 対象 Issue にコメントで親 Issue 番号を記載し、TODO に記録する |

---

## 禁止

- `gh issue create` より前に本 skill を実行する
- `project_id` / `item_id` を推測で埋めてコマンドを生成する
- Status / Priority の根拠を記録せずに更新する
- 未実施の項目を Output B に書かず終了する
- blocked-by / sub-issue を Issue 本文と Project 側で乖離したまま放置する
- 本 skill 内で `gh issue create` を再実行する

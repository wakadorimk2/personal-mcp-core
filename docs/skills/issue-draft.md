# issue-draft

**種類**: draft
**正本**: このファイル（`docs/skills/issue-draft.md`）
**Claude用アダプタ**: `.claude/skills/issue-draft/SKILL.md`
**Codex用アダプタ**: `.codex/skills/issue-draft/SKILL.md`

---

## Mission

`clarify-request` の確定済み構造化メモを受け取り、
GitHub Issue 本文として貼れる草案 Markdown と
`gh issue create` に渡せる title/body 最小セットを生成する。

---

## 前提条件（必須）

- **clarify-request が完了していること** — 構造化メモ（Output B）が人間に確認済みであること
- clarify 未完了のまま draft を確定してはならない
- 構造化メモの TBD 項目が残っている場合は、draft 生成前に人間へ再確認を求める

---

## Rules（絶対）

- **Goal / Scope / Acceptance Criteria / Non-goal の 4 要素を必須とする** — いずれか欠けた場合は生成を拒否し、不足要素を指摘する
- **Scope は In / Out 形式で記述する** — Out を省略しない
- **AC はチェックリスト形式にする** — `- [ ] ` プレフィックスを使う
- **AC は検証可能な文にする** — 曖昧語（「適切に」「きれいに」「十分に」「正しく」「うまく」）を禁止する
- **出力はそのまま Issue 本文に貼れる Markdown にする** — Markdown 以外の形式を混在させない
- **草案は DRAFT ラベルを付けて出力する** — 人間が確認するまで確定扱いしない

---

## 曖昧語禁止リスト（AC 検証ルール）

以下の語を AC に含めてはならない。含まれている場合は具体化を求める。

| 禁止語 | 代替例 |
|---|---|
| 適切に | `<具体的な値/状態>` になっている |
| きれいに | `<具体的な形式/構造>` に従っている |
| 十分に | `<数値・閾値>` 以上／以下 |
| 正しく | `<期待する出力/状態>` と一致する |
| うまく | `<動作条件>` を満たす |
| 良い | `<測定可能な基準>` を満たす |
| 快適に | `<具体的な操作・応答条件>` |

---

## Inputs

- `clarify-request` Output B の確定済み構造化メモ（必須）
- Issue タイトル候補（任意。なければ Goal から生成する）

---

## Procedure（作業手順）

1. **前提確認** — clarify 完了・TBD 残存・4 要素の充足を確認する
2. **依存関係確認** — Dependencies / Blockers が未解消の場合、下記「依存未解消時の扱い」に従う
3. **AC 検証** — 禁止語が含まれていないか確認し、あれば具体化を求める
4. **Issue 草案 Markdown（Output A）を生成する**
5. **title/body 最小セット（Output B）を生成する**
6. **DRAFT ラベルを付けて出力し、人間の確認を求める**

---

## 依存未解消時の扱い

依存 Issue・PR・外部要因が未解消のまま draft を生成する場合は以下を必ず行う。

1. Issue 草案の冒頭に `> **[BLOCKED]** 依存未解消: <依存先>` を挿入する
2. Dependencies セクションに依存先を明記し、解消条件を 1 行で記す
3. Blockers セクション（Issue 草案の末尾）に未解消理由を記載する
4. DRAFT ラベルは外さない — 依存解消後に改めて確定とする

例（#103 が未解消の場合）:

```markdown
> **[BLOCKED]** 依存未解消: #103 が完了するまでこの Issue は着手不可

## Dependencies

- blocked by #103（clarify-request Output B 形式の確定待ち）

## Blockers

- #103 未マージ: clarify-request の出力形式が確定していないため、入力仕様が固まらない
```

---

## Output A: Issue 草案 Markdown（コピペ用）

> このブロックをそのまま GitHub Issue 本文に貼れる。
> `<!-- [DRAFT] -->` コメントが残っている間は確定扱いしないこと。

```markdown
<!-- [DRAFT] 人間確認前に確定扱いしないこと -->

## Goal

<このIssueで解決する問題・達成すること（1〜3文）>

## Scope

**In（対象）**
- <対象1>
- <対象2>

**Out（除外）**
- <除外1>
- <除外2>

## Acceptance Criteria

- [ ] <検証可能な完了条件1>
- [ ] <検証可能な完了条件2>
- [ ] <検証可能な完了条件3>

## Non-goal

- <今回やらないこと1（理由）>
- <今回やらないこと2（理由）>

## Dependencies

- <先行 Issue・PR・外部要因（なければ「なし」）>

## Blockers

- <未解消の阻害要因（なければ「なし」）>

## Notes

<補足・背景・仮定（任意）>
```

---

## Output B: title/body 最小セット

> `gh issue create` に渡す最小の 2 要素。実行コマンドは参考として末尾に示す。

**title**（コピペ用、50字以内）:
```
<Goal の要約>
```

**body**（コピペ用 — Output A の Markdown をそのまま貼る）:
```markdown
<!-- [DRAFT] 人間確認前に確定扱いしないこと -->

## Goal
...（Output A の内容）
```

> **参考**: `gh issue create` で渡す場合は以下の形式を使う（実行は Codex 側）
> ```bash
> gh issue create --title "<title>" --body-file <body.md>
> ```

---

## 前提未充足時の対応

| 状況 | 対応 |
|---|---|
| clarify 未完了 | draft 生成を拒否し、`/clarify-request` を先に完了するよう伝える |
| TBD 項目が残存 | TBD 箇所を列挙し、確定 or 明示的 TBD 合意を求める |
| 4 要素のいずれかが欠落 | 欠落要素を指摘し、補足を求める |
| AC に曖昧語が含まれる | 該当語を引用し、具体化した代替案を提示して確認を求める |
| 依存 Issue が未解消 | 「依存未解消時の扱い」に従い BLOCKED 注記を挿入する |

---

## 禁止

- clarify 未完了のまま draft を確定する
- Goal / Scope / AC / Non-goal のいずれかを省略した草案を出力する
- AC に曖昧語を含める
- `gh issue create` を実際に実行する（draft 生成のみ）
- DRAFT ラベルなしで最終草案として出力する

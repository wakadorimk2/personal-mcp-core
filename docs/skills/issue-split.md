# issue-split

**種類**: split
**正本**: このファイル（`docs/skills/issue-split.md`）
**Claude用アダプタ**: `.claude/skills/issue-split/SKILL.md`
**Codex用アダプタ**: `.codex/skills/issue-split/SKILL.md`

---

## Mission

`issue-draft` で草案化した大きな Issue を受け取り、
独立して完了判定できる子 Issue に分割し、
依存関係を DAG（有向非巡回グラフ）として Markdown で表現する。

---

## 位置づけ

```
/clarify-request  →  /issue-draft  →  [/issue-split]  →  /issue-create
                                        ↑ オプション手順
                                          大きすぎる Issue にのみ使う
```

- `issue-draft` が完了し、人間が「分割が必要」と判断した場合にのみ実行する
- `issue-split` の出力（子 Issue 草案群）は、それぞれ `issue-create` で個別に登録する
- 分割しない場合は `issue-draft` → `issue-create` の通常フローに戻る

---

## 前提条件（必須）

- **`issue-draft` が完了していること** — 構造化草案（Output A）が人間に確認済みであること
- **人間が「分割が必要」と明示的に判断していること** — AI が自動的に分割を推奨・実行してはならない
- 草案に TBD 項目が残っている場合は、分割前に解消または明示的 TBD 合意を求める

---

## Rules（絶対）

### 分割の粒度

1. **子 Issue は独立して完了判定できる粒度にする**
   - 「他の子 Issue がマージされていないと AC 確認できない」状態にしない
   - AC はその子 Issue 単体のスコープ内で検証できること

2. **依存関係は最小化する**
   - 「全部の子 Issue が先行 Issue に依存する」構造を避ける
   - 必要な依存のみを明記し、不要な依存エッジを加えない

3. **循環依存を作らない**
   - A → B → A のような循環は絶対に禁止する
   - DAG（有向非巡回グラフ）であることを出力前に確認する

4. **分割数は最小限にする**
   - 「実行できない理由を作るための分割」は禁止する
   - 子 Issue が 6 件以上になる場合は、分割の必要性を人間に再確認する

### 命名

5. **子 Issue のタイトルは親 Issue のタイトルから導出する**
   - 形式: `<親タイトルの核心語>: <子Issueの固有作業>`
   - 例: 親が「add issue-split skill」なら子は「add issue-split skill: define doc spec」など

### 依存表現

6. **依存関係は `blocked by #<番号>` の形式で表現する**
   - 既存の `blocked by #104` のような表現と統一する
   - 子 Issue 同士の依存は、分割案の段階では仮番号を使わず「子Issue-A → 子Issue-B」の記法で示す

7. **親 Issue との関係を明示する**
   - 子 Issue は全て親 Issue の `sub-issue of #<親番号>` として位置づける
   - ただし実際の GitHub relationship 設定は `issue-project-meta` の責務とする

---

## 禁止

- `issue-draft` 未完了のまま分割案を生成する
- 人間の明示的な「分割が必要」の判断なしに分割を推奨・実行する
- 循環依存を含む DAG を出力する
- 子 Issue が単体で AC 確認できない粒度にする
- 分割案の段階で GitHub Issue 作成コマンドを生成する（作成は `issue-create` の責務）
- 6 件以上の子 Issue を人間の再確認なしに提示する
- 依存がない子 Issue 間に不要な依存エッジを追加する

---

## Inputs

| 項目 | 必須 | 説明 |
|---|---|---|
| `parent_draft` | 必須 | `issue-draft` Output A の確定済み Markdown |
| `parent_title` | 必須 | 親 Issue のタイトル候補（50字以内） |
| `split_hint` | 任意 | 人間からの分割の観点ヒント（例:「実装フェーズ別に分ける」） |

---

## Procedure（作業手順）

1. **前提確認** — `issue-draft` 完了・人間の分割判断・TBD 残存を確認する
2. **分割観点の確認** — `split_hint` があればそれに従い、なければ親 Issue の Scope と AC から分割観点を導出して人間に確認する
3. **子 Issue 一覧を草案化する**（Output A）
4. **依存 DAG を生成する**（Output B）
5. **各子 Issue の草案 Markdown を生成する**（Output C）
6. **DAG に循環がないことを確認してから出力する**
7. **DRAFT ラベルを付けて出力し、人間の確認を求める**

---

## Output A: 子 Issue 一覧（コピペ可能なテンプレート）

> 人間が確認・修正しやすいよう、全子 Issue を一覧形式で示す。

```markdown
<!-- [DRAFT] 分割案 — 人間確認前に確定扱いしないこと -->

## 分割案サマリ

**親 Issue**: <親タイトル>
**分割数**: <N>件
**分割観点**: <観点の説明（例: 実装フェーズ別）>

| # | 子 Issue タイトル | 依存 | 独立完了可否 |
|---|---|---|---|
| 子-1 | <タイトル> | なし | ✅ |
| 子-2 | <タイトル> | 子-1 完了後 | ✅ |
| 子-3 | <タイトル> | なし | ✅ |
```

---

## Output B: 依存 DAG（Markdown）

> 子 Issue 間の依存関係を有向非巡回グラフとして示す。
> 矢印の向きは「A → B」= 「B は A が完了してから着手できる」を意味する。

````markdown
## 依存 DAG

```
[子-1: <タイトル略称>]
        ↓
[子-2: <タイトル略称>]

[子-3: <タイトル略称>]  ← 独立（依存なし）
```

**DAG 検証**: 循環なし ✅

| エッジ | 方向 | 理由 |
|---|---|---|
| 子-1 → 子-2 | 子-1 が先行 | <依存理由1文> |
````

---

## Output C: 各子 Issue の草案 Markdown（コピペ可能）

> 各子 Issue を `issue-draft` Output A 形式で生成する。
> このブロックを `/issue-create` にそのまま渡せる。

```markdown
<!-- [DRAFT] 子-1 草案 — 人間確認前に確定扱いしないこと -->

## Goal

<子 Issue が解決する問題・達成すること（1〜3文）>

## Scope

**In（対象）**
- <対象1>

**Out（除外）**
- <除外1>
- 他の子 Issue のスコープ（<子-2>, <子-3>）

## Acceptance Criteria

- [ ] <この子 Issue 単体で検証できる完了条件1>
- [ ] <この子 Issue 単体で検証できる完了条件2>

## Non-goal

- <今回やらないこと（他の子 Issue で対応するものを含む）>

## Dependencies

- sub-issue of #<親Issue番号>（作成後に issue-project-meta で設定）
- blocked by <子-X>（子 Issue 間依存がある場合。作成後に実番号で更新）

## Blockers

- なし（または未解消の阻害要因）

## Notes

- 親 Issue: <親タイトル>
- 分割観点: <観点>
```

---

## 具体例（issue-split skill 自体を分割する場合）

### 前提

- 親 Issue: `add issue-split skill`
- 分割観点: 成果物ごと（doc spec / Claude adapter / CLAUDE.md 更新）

### Output A（分割案サマリ）

```markdown
<!-- [DRAFT] 分割案 — 人間確認前に確定扱いしないこと -->

## 分割案サマリ

**親 Issue**: add issue-split skill
**分割数**: 3件
**分割観点**: 成果物ごと（doc spec → Claude adapter → docs登録）

| # | 子 Issue タイトル | 依存 | 独立完了可否 |
|---|---|---|---|
| 子-1 | add issue-split skill: define doc spec | なし | ✅ |
| 子-2 | add issue-split skill: add Claude adapter | 子-1 完了後 | ✅ |
| 子-3 | add issue-split skill: register in CLAUDE.md | 子-2 完了後 | ✅ |
```

### Output B（依存 DAG）

````markdown
## 依存 DAG

```
[子-1: define doc spec]
        ↓
[子-2: add Claude adapter]
        ↓
[子-3: register in CLAUDE.md]
```

**DAG 検証**: 循環なし ✅

| エッジ | 方向 | 理由 |
|---|---|---|
| 子-1 → 子-2 | 子-1 が先行 | adapter は doc spec が確定してから書く |
| 子-2 → 子-3 | 子-2 が先行 | CLAUDE.md 登録は skill ファイル追加後に行う |
````

---

## issue-create / issue-project-meta との連携

分割案が人間に承認された後のフローは以下のとおり：

```
[issue-split Output C（子-N 草案）]
        ↓
/issue-create（子-N を個別に登録）
        ↓
/issue-project-meta（sub-issue of / blocked-by を設定）
```

- **`issue-split` は Issue を作成しない** — コピペ可能な草案を生成するだけ
- **relationship（sub-issue / blocked-by）の設定は `issue-project-meta` の責務**
- `issue-create` の `blocked by #104` 前提（ラベル確認手順）はそのまま有効

---

## 前提未充足時の対応

| 状況 | 対応 |
|---|---|
| issue-draft 未完了 | 分割生成を拒否し、`/issue-draft` を先に完了するよう伝える |
| 人間の分割判断がない | 自動分割せず、「分割が必要ですか？」と確認する |
| TBD 項目が残存 | TBD 箇所を列挙し、確定 or 明示的 TBD 合意を求める |
| 子 Issue が 6 件以上になる | 6 件以上の一覧を出力する前に人間に再確認する |
| DAG に循環が検出された | 循環箇所を明示し、依存関係の修正案を提示して確認を求める |
| 子 Issue が単体で AC 確認できない | 該当 AC を引用し、子 Issue の境界を修正して再提示する |

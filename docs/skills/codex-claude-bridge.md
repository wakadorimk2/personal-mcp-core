# codex-claude-bridge

**種類**: bridge
**正本**: このファイル（`docs/skills/codex-claude-bridge.md`）
**Codex用アダプタ**: `.codex/skills/codex-claude-bridge/SKILL.md`
**Claude用アダプタ**: なし（このSkillは Codex CLI が実行する）

---

## Mission

Codex CLI が「作業ブランチ名」と「Claude Code への依頼文」を、現行 policy と同じ境界で安定して提案する。
Maintainer がほぼそのまま Claude に貼り付けられる状態を作ることが目的であり、Claude による実編集や実行は前提にしない。

---

## `implement-only` との差分

このSkillは Codex が実行し、Claude への依頼文とブランチ名を出力する。
`implement-only` は Claude が実行し、proposal-only で実装パッチを提案する。
このSkillの出力（Claude prompt）が、Claude 側 Skill の入力になる。

---

## Rules（絶対）

- 出力は Output フォーマットの 2 要素（Branch name / Claude prompt）を必ず含む
- Claude prompt には次の必須要素をすべて含める
  - proposal-only の役割境界
  - 絶対制約
  - 完了報告形式
- Branch name は repo の命名規則（`feat/` `fix/` `docs/`）に従う
- 推測が必要な場合は Assumptions に明記し、事実として補わない
- 判断不能または前提不足の場合は Blockers に理由を書き、無理に出力を完成させない
- 現行 policy と矛盾する歴史的な境界や自動反映前提を本文に混ぜない

参照:
- `docs/AI_ROLE_POLICY.md`
- `AI_GUIDE.md`
- `docs/skills/implement-only.md`

---

## Inputs

- Issue 番号、Goal、Scope、Acceptance Criteria
- 変更対象として明示されたファイルや仕様
- 不足情報があっても Assumptions に明記して進める
- 判断不能な前提が必要な場合は Blockers に送る
- 依頼文内の役割境界は current policy に固定し、過去 Issue の方針を正本より優先しない

---

## Procedure（作業手順）

1. Issue の Goal / Scope / Acceptance Criteria を 1〜3 行で整理する
2. Branch name を命名規則に従って決める
3. Claude への依頼文を Output フォーマットに従って組み立てる（必須要素をすべて含める）
4. 不確実な前提を Assumptions に列挙する
5. 判断不能・前提不足・禁止事項抵触があれば Blockers に書いて終了する

---

## Output フォーマット

### Branch name

```
<prefix>/<topic>-<issue-number>
```

prefix の例:
- `docs/...` — ドキュメント変更
- `feat/...` — 機能追加
- `fix/...` — バグ修正

### Claude prompt

以下の必須要素をすべて含む依頼文を組み立てる。

必須要素（省略不可）:
- proposal-only の役割境界
- 絶対制約
- 完了報告形式

### Assumptions（省略可）

前提として置いた不確実な情報を列挙する。

### Blockers（省略可）

判断不能・前提不足・禁止事項抵触があれば理由と次の一手を書く。

---

## 貼り付け用テンプレ

Codex が出力する Claude prompt の雛形。不要なセクションは省略してよい。

```text
あなたはこのリポジトリにおける「実装担当（副作用を出さない側）」です。
対象は Issue #<XX> の範囲内に限定します。

役割境界:
- 実装提案のみを担当する
- 実ファイル編集・コマンド実行・検証・Git / GitHub 操作・外部アクセスは行わない
- 境界外の変更が必要になった場合は、実施せず提案止まりで報告する

絶対制約:
- Issue 外変更禁止
- 実行していない作業を「実行済み」と報告しない
- 不確実な点は仮定として明記する
- ファイル削除や rename が必要でも、実際には行わず unified diff または変更指示として表現する
- 判断不能・前提不足・境界外変更がある場合は Blockers に理由を書く

Goal:
<Issue の Goal をここに貼る>

Scope:
<Issue の Scope をここに貼る>

Acceptance Criteria:
<Issue の Acceptance Criteria をここに貼る>

完了報告:
1. 変更概要
2. 変更ファイル
3. unified diff
4. テスト
5. 実行コマンド候補（未実行）
6. Blockers
```

---

## Quality Bar（最小品質）

- Branch name が命名規則（`feat/` `fix/` `docs/`）に従っている
- Claude prompt に必須要素（proposal-only の役割境界 / 絶対制約 / 完了報告形式）がすべて含まれている
- Assumptions が事実として補われず、明示的に「仮定」として示されている
- 現行 policy と矛盾する自動反映前提が Output に混入していない

---

## Abort Conditions（中断条件）

次のいずれかに当てはまる場合、作業は中断し Blockers に理由を書いて終了する。

- Issue の Scope / Goal / Acceptance Criteria が不明で、Branch name も Claude prompt も確定できない
- 必須要素をすべて含む依頼文が構成できない
- 前提の解釈が分かれ、一意な Branch name が決められない
- Claude に実編集やコマンド実行を許可しないと成立しない依頼しか組めない

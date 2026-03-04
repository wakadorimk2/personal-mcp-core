# codex-claude-bridge

**種類**: bridge
**正本**: このファイル（`docs/skills/codex-claude-bridge.md`）
**Codex用アダプタ**: `.codex/skills/codex-claude-bridge/SKILL.md`
**Claude用アダプタ**: なし（このSkillは Codex CLI が実行する）

---

## Mission

Codex CLI が「作業ブランチ名」と「Claude Code への依頼文」を安定した形式で提案できる最小出力フォーマット（v1）を定義する。
Maintainer がほぼそのまま Claude に貼れる状態にすることが目的であり、実装そのものは行わない。

---

## `implement-only` との差分

このSkillは Codex が実行し、Claude への依頼文とブランチ名を出力する。
`implement-only` は Claude が実行し、実装パッチを unified diff で提案する。
このSkillの出力（Claude prompt）が、`implement-only` など Claude 側 Skill の入力になる。

---

## Rules（絶対）

- 出力は Output フォーマット v1 の 2 要素（Branch name / Claude prompt）を必ず含む
- Claude prompt には「必須制約」をすべて含める
- Branch name は repo の命名規則（`feat/` `fix/` `docs/`）に従う
- 推測が必要な場合は Assumptions に明記し、事実として補わない
- 判断不能または前提不足の場合は Blockers に理由を書き、無理に出力を完成させない
- v2 以降の拡張案や設計議論は本文に混ぜず、Blockers または別 Issue 提案に留める

参照:
- `docs/AI_ROLE_POLICY.md`
- `AI_GUIDE.md`

---

## Inputs

- Issue 番号、Goal、Scope、Acceptance Criteria
- 変更対象として明示されたファイルや仕様
- 不足情報があっても Assumptions に明記して進める
- 判断不能な前提が必要な場合は Blockers に送る

---

## Procedure（作業手順）

1. Issue の Goal / Scope / Acceptance Criteria を 1〜3 行で整理する
2. Branch name を命名規則に従って決める
3. Claude への依頼文を Output フォーマット v1 に従って組み立てる（必須制約を必ず含める）
4. 不確実な前提を Assumptions に列挙する
5. 判断不能・前提不足・禁止事項抵触があれば Blockers に書いて終了する

---

## Output フォーマット（v1）

### Branch name

```
<prefix>/<topic>-<issue-number>
```

prefix の例:
- `docs/...` — ドキュメント変更
- `feat/...` — 機能追加
- `fix/...` — バグ修正

### Claude prompt

以下の「必須制約」をすべて含む依頼文を組み立てる。

必須制約（省略不可）:
- 実装提案のみ（diff または仕様案の提示）
- コマンド実行禁止
- `gh` 操作禁止
- 外部アクセス禁止
- Issue 外変更禁止

### Assumptions（省略可）

前提として置いた不確実な情報を列挙する。

### Blockers（省略可）

判断不能・前提不足・禁止事項抵触があれば理由と次の一手を書く。

---

## 貼り付け用テンプレ（v1）

Codex が出力する Claude prompt の雛形。不要なセクションは省略してよい。

```text
あなたはこのリポジトリにおける「実装担当（副作用を出さない側）」です。
対象は Issue #<XX> の範囲内に限定します。

制約:
- 実装提案のみ（diff または仕様案）
- コマンド実行禁止
- gh 操作禁止
- 外部アクセス禁止
- Issue 外変更禁止

Goal:
<Issue の Goal をここに貼る>

Scope:
<Issue の Scope をここに貼る>

Acceptance Criteria:
<Issue の Acceptance Criteria をここに貼る>

出力順:
1. 変更概要
2. 変更ファイル
3. unified diff
4. テスト
5. 実行コマンド候補
6. Blockers
```

---

## Quality Bar（最小品質）

- Branch name が命名規則（`feat/` `fix/` `docs/`）に従っている
- Claude prompt に必須制約がすべて含まれている
- Assumptions が事実として補われず、明示的に「仮定」として示されている
- v2 以降の話が Output に混入していない

---

## Abort Conditions（中断条件）

次のいずれかに当てはまる場合、作業は中断し Blockers に理由を書いて終了する。

- Issue の Scope / Goal / Acceptance Criteria が不明で、Branch name も Claude prompt も確定できない
- 必須制約をすべて含む依頼文が構成できない
- 前提の解釈が分かれ、一意な Branch name が決められない

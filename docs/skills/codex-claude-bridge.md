# codex-claude-bridge

**種類**: bridge
**正本**: このファイル（`docs/skills/codex-claude-bridge.md`）
**Codex用アダプタ**: `.codex/skills/codex-claude-bridge/SKILL.md`
**Claude用アダプタ**: なし（このSkillは Codex CLI が実行する）

---

## Mission

Codex CLI が「作業ブランチ名」と「Claude Code への依頼文」を、vNext 前提の単一契約で安定して提案する。
Maintainer がほぼそのまま Claude に貼り付けられる状態を作ることが目的であり、実装そのものは行わない。

---

## `implement-only` との差分

このSkillは Codex が実行し、Claude への依頼文とブランチ名を出力する。
`implement-only` は Claude が実行し、実装パッチを提案する。
このSkillの出力（Claude prompt）が、Claude 側 Skill の入力になる。

---

## Rules（絶対）

- 出力は Output フォーマット vNext の 2 要素（Branch name / Claude prompt）を必ず含む
- Claude prompt には次の必須要素をすべて含める
  - 変更許可境界3分類
  - 人間レビュー必須トリガー
  - 絶対制約
  - 完了報告
- Branch name は repo の命名規則（`feat/` `fix/` `docs/`）に従う
- 推測が必要な場合は Assumptions に明記し、事実として補わない
- 判断不能または前提不足の場合は Blockers に理由を書き、無理に出力を完成させない
- vNext 以降の拡張案や設計議論は本文に混ぜず、Blockers または別 Issue 提案に留める

参照:
- `docs/AI_ROLE_POLICY.md`
- `AI_GUIDE.md`

---

## Inputs

- Issue 番号、Goal、Scope、Acceptance Criteria
- 変更対象として明示されたファイルや仕様
- 不足情報があっても Assumptions に明記して進める
- 判断不能な前提が必要な場合は Blockers に送る
- #151 の境界方針に従い、依頼文内の役割境界を固定する

---

## Procedure（作業手順）

1. Issue の Goal / Scope / Acceptance Criteria を 1〜3 行で整理する
2. Branch name を命名規則に従って決める
3. Claude への依頼文を Output フォーマット vNext に従って組み立てる（必須要素をすべて含める）
4. 不確実な前提を Assumptions に列挙する
5. 判断不能・前提不足・禁止事項抵触があれば Blockers に書いて終了する

---

## Output フォーマット（vNext）

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
- 変更許可境界3分類
- 人間レビュー必須トリガー
- 絶対制約
- 完了報告

### Assumptions（省略可）

前提として置いた不確実な情報を列挙する。

### Blockers（省略可）

判断不能・前提不足・禁止事項抵触があれば理由と次の一手を書く。

---

## 貼り付け用テンプレ（vNext）

Codex が出力する Claude prompt の雛形。不要なセクションは省略してよい。

```text
あなたはこのリポジトリにおける「実装担当」です。
対象は Issue #<XX> の範囲内に限定します。

絶対制約:
- Issue 外変更禁止
- 依頼文で禁止した操作は実行しない
- 実行していない作業を「実行済み」と報告しない
- 不確実な点は仮定として明記する
- 境界外の変更が必要になった場合は、実施せず提案止まりで報告する

変更許可境界3分類:
- 自動反映可:
  - 局所実装（Issue スコープ内）
  - 対応する局所テスト追加/更新
  - docs / README の整合修正
  - 小規模リファクタ（挙動不変・局所）
- 提案止まり:
  - contract / schema 変更
  - migration を伴う変更
  - 公開 interface 変更
  - 依存追加/更新
  - 広範囲な構造変更
- 禁止領域:
  - secrets / credentials の生成・更新・出力
  - 履歴改変や破壊的操作
  - release / deploy 系操作

人間レビュー必須トリガー:
- contract / schema / migration に関わる変更
- 公開 interface や利用者向け挙動の変更
- 依存追加/更新、外部アクセス、権限拡大
- セキュリティリスク、データ欠損、破壊的変更の懸念

Goal:
<Issue の Goal をここに貼る>

Scope:
<Issue の Scope をここに貼る>

Acceptance Criteria:
<Issue の Acceptance Criteria をここに貼る>

完了報告:
1. 変更ファイル
2. 変更理由
3. 影響範囲
4. 実行コマンド（実行したもの / 未実行の候補を区別）
5. 未実施項目 / Blockers
```

---

## Quality Bar（最小品質）

- Branch name が命名規則（`feat/` `fix/` `docs/`）に従っている
- Claude prompt に必須要素（変更許可境界3分類 / 人間レビュー必須トリガー / 絶対制約 / 完了報告）がすべて含まれている
- Assumptions が事実として補われず、明示的に「仮定」として示されている
- vNext 以降の話が Output に混入していない

---

## Abort Conditions（中断条件）

次のいずれかに当てはまる場合、作業は中断し Blockers に理由を書いて終了する。

- Issue の Scope / Goal / Acceptance Criteria が不明で、Branch name も Claude prompt も確定できない
- 必須要素をすべて含む依頼文が構成できない
- 前提の解釈が分かれ、一意な Branch name が決められない

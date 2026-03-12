# daily input mode contract v1

> 関連 Issue: #188, #180, #181, #199
> 関連 PR: #183, #205
>
> この文書は quick / tag / text モードの責務境界と、
> UX 比較時の計測前提を MVP 向けに固定する。

---

## 1. Goal

- quick 即保存と #180（候補タップ後の編集可能フロー）の混同を防ぐ
- mode ごとの責務差分を明文化し、分析時の比較単位を揃える
- 最低限の計測メタデータ要件を定義する

---

## 2. Mode responsibilities

| mode | 主目的 | 保存トリガ | 編集前提 |
|---|---|---|---|
| `quick` | one-tap capture（最短記録） | quick チップタップで即保存 | 保存前編集なし |
| `tag` | 候補タグ起点入力 | 明示 submit | 候補選択後の編集可 |
| `text` | 自由記述入力 | 明示 submit | 常に編集可 |

補足:

- `quick` は「即時記録」の専用導線とする。
- `tag` は #180 の「候補タップ後に編集可能」要件を満たす主導線とする。
- `text` は候補が合わない場合のフォールバック導線とする。

---

## 3. #180 との整合ルール

- #180 の候補 UX 比較（候補選択から編集まで）は `tag` / `text` トラックで評価する。
- `quick` は比較対象から除外し、別トラックの capture 導線として扱う。
- これにより「候補品質評価」と「即時記録速度評価」を同一指標で混ぜない。

---

## 4. Quick 即保存の許容条件

- quick チップをタップした操作のみ即保存を許容する。
- quick は入力途中の編集ステップを挟まない。
- 保存後の修正は別イベント追記で扱う（既存 event の書き換えはしない）。

非スコープ:

- quick に「保存前編集」を導入する UI 変更
- quick 保存取り消しフローの実装

---

## 5. 計測メタデータ要件（MVP）

`input_submitted`（または同等イベント）で次を記録する。

| key | 型 | 値例 | 用途 |
|---|---|---|---|
| `mode` | string | `quick` / `tag` / `text` | モード別比較 |
| `save_type` | string | `instant` / `manual` | 即保存と手動保存の分離 |
| `edited_before_submit` | bool | `true` / `false` | 候補後編集の有無判定 |
| `trigger` | string | `quick_chip` / `candidate_tag` / `text_submit` | 保存を発火した UI アクションの識別 |

推奨（任意）:

- `candidate_source`（`recent` / `today_frequent` / `7d_frequent` / `fixed` / `free_text`）

補足:

- dashboard 系導線では、`trigger` に `candidate_quick_save` や `dashboard_submit` など、より具体的な値を記録してよい。
- 比較集計条件の正本は後続分析 docs（#199）で定義する。

---

## 6. 運用 / 互換方針

- 既存ログに上記メタデータが無い期間は、分析時に `unknown` または除外対象として扱う。
- reader tolerance で欠損を許容し、過去データの後方互換レイヤは追加しない。
- 実装側はこの契約に整合する範囲で telemetry を記録し、比較条件の厳密化は別 docs で扱う。

---

## 7. Decision summary

- quick は one-tap capture 専用導線として維持する。
- #180 の候補 UX 比較は tag/text トラックで扱う。
- 比較混同を防ぐ最小メタデータは `mode` / `save_type` / `edited_before_submit` / `trigger` とする。

# review-diff

`docs/CODEX_RUNBOOK.md` の §2 Review 章を、Codex CLI 向けの固定テンプレとして切り出した skill。
差分レビュー時の観点と指摘順を固定し、finding をリスク順に、要約より先に出す契約を定義する。
人間向けの意図説明はこの文書に置き、Codex が実行するときの正は `.codex/skills/review-diff/SKILL.md` とする。
つまり `review-diff` は docs だけで完結せず、Codex 実行版アダプタとセットで維持する。

## Purpose

差分レビューの観点と出力順序を固定する。

## Input

- PR 番号（任意）
- 比較対象 diff
- 関連 Issue（任意）

## Fixed Procedure

以下の手順をこの順序で実行する。省略・並べ替え・別手順への置き換えはしない。

1. 差分の全体像を要約する
2. 変更ファイルを影響度順に並べる
3. 各ファイルを以下の観点で確認する
   - 回帰: 既存の動作を壊す変更がないか
   - 仕様逸脱: Issue スコープ外の変更が混ざっていないか
   - テスト欠落: 挙動変更に対応するテストがないか
4. finding をリスク順（HIGH → MEDIUM → LOW）で列挙する
5. 根拠が不足する場合は断定せず、追加で見るべきファイルまたは前提を 1 行で示す

詳細な位置づけと停止条件は `docs/CODEX_RUNBOOK.md` を参照する。この skill は runbook 全体の代替ではなく、差分レビュー部分のテンプレである。

## Failure Handling

- 根拠が確認できない finding は断定せず `Open Questions` に分類する
- Issue スコープ外変更を発見した場合は finding として HIGH リスクに列挙し、レビュー続行可否を明記する
- `ruff` または `pytest` の失敗がレビュー対象から確認できる場合は、`Next Step` に次の一手を 1 行で出力する

## Output Format

出力は PR コメントまたは Issue コメントにそのまま貼れる Markdown とし、3 回実行しても同じ見出し構造を維持する。
必ず以下の見出しをこの順序で出力する。

## Findings

finding がない場合も `None` と明記する。
finding がある場合はリスク順（HIGH / MEDIUM / LOW）で列挙する。

## Open Questions

根拠が不足し断定できない点を列挙する。ない場合は `None` と明記する。
追加で見るべきファイルまたは前提を 1 行で示す。

## Change Summary

- 変更ファイル数
- 追加/削除行数
- 変更目的を 2〜5 行で要約する

## Next Step

- `ruff` または `pytest` の失敗がレビュー対象から確認できる場合は、最小修正または停止理由を 1 行で書く
- HIGH リスク finding がある場合は、レビュー続行可否を 1 行で書く
- 上記のどちらにも当てはまらない場合は `None` と明記する

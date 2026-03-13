---
name: review-preflight
description: merge 前 review の検査と報告を標準化する skill。修正は行わず、観点に沿った検査結果を報告する。
---

# review-preflight

Claude Code 向けの実行 contract。
仕様の正本は [`docs/CODEX_RUNBOOK.md`](../../../docs/CODEX_RUNBOOK.md) Appendix B とする。

## Goal

merge 前 review の安全確認と 4 観点の意味的整合チェックを固定した順序で実施し、結果を報告する。
**本 skill は修正を行わない。** 検査と報告のみが責務であり、修正は別 skill（`minimal-safe-impl` など）に委譲する。

## Inputs

- `pr_or_diff`（PR 番号または差分）
- `issue_ref`（対応する Issue 番号。Scope Guard チェックに使用）
- base branch（任意）
- 現在の作業ツリー（または Codex が取得したコマンド実行結果）

## Procedure

以下の順序で実施する（Claude はコマンドを実行しない。提供された結果のみ参照する）。

1. 作業ツリーの差分を確認（提供されていれば `git status` / `git diff` の結果を参照）
2. `ruff` / `pytest` の結果を確認（提供されていれば参照。未提供時は `Failures` に不足情報として記録）
3. 4 観点チェック（下記 Review Axes を参照）
4. Output Format に沿った報告

自動修正・再試行ループは行わない。

## Review Axes（4本柱）

### 1) Contract Consistency

イベント契約の照合は、次の正本のみを使う（優先順に記載）。

1. `docs/event-contract-v1.md`（最優先）
2. `docs/domain-extension-policy.md`（domain/allowlist の正本）
3. `docs/kind-taxonomy-v1.md`（kind taxonomy の正本）

`docs/architecture.md` と `AI_GUIDE.md` は補助ガイドとして扱い、正本判定には使わない。

### 2) Scope Guard

Issue の Goal / Scope / Acceptance Criteria / Non-goals と差分を照合し、範囲外変更の混入を確認する。

### 3) Migration Awareness

破壊的変更や移行説明が必要な差分かを確認し、説明不足を報告する。

### 4) Docs-Impl Consistency

ドキュメント記述と実装差分の意味が一致しているかを確認する。

## Output Format

出力は PR コメントにそのまま貼れる Markdown とし、以下の見出し構造を維持する。

## Summary

短い結果サマリー（検査対象 / 判定 / レビュー継続可否）

## Preflight Checks

- `git status`: `PASS` / `FAIL`
- `git diff`: `PASS` / `FAIL`
- `ruff`: `PASS` / `FAIL`
- `pytest`: `PASS` / `FAIL`
- `contract`: `PASS` / `WARN` / `FAIL`
- `scope`: `PASS` / `WARN` / `FAIL`
- `migration`: `PASS` / `WARN` / `FAIL`
- `docs-impl`: `PASS` / `WARN` / `FAIL`

## Failures

失敗したチェックの詳細。失敗がない場合も `None` と明記する。
各項目: `Failure` / `Repro` / `Likely Cause`

## Next Step

- 失敗あり: `修正は別 skill（minimal-safe-impl など）へ委譲。review-preflight は報告のみ。`
- 失敗なし: `レビュー開始可。`

## Constraints

- 修正を行わない（本 skill は検査と報告のみ）
- コマンドを実行しない（提供された実行結果のみ参照する）
- 外部 web 検索・任意リモートコンテンツへのアクセスをしない
- 自動修正・再試行ループをしない
- 報告は `Summary / Preflight Checks / Failures / Next Step` の順で出力する

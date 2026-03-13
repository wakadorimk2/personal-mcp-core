---
name: review-preflight
description: merge 前 review の検査と報告を標準化する skill。修正は行わず、観点に沿った検査結果を報告する。
---

# review-preflight

Codex CLI 向けの実行 contract。
仕様の正本は [`docs/CODEX_RUNBOOK.md`](../../../docs/CODEX_RUNBOOK.md) Appendix B とする。

## Goal

merge 前 review の安全確認と 4 観点の意味的整合チェックを固定した順序で実施し、結果を報告する。
**本 skill は修正を行わない。** 検査と報告のみが責務であり、修正は別 skill（`minimal-safe-impl` など）に委譲する。

## Inputs

- `pr_or_diff`（PR 番号または差分）
- `issue_ref`（対応する Issue 番号。Scope Guard チェックに使用）
- base branch（任意。未指定時は upstream または `main`）
- 現在の作業ツリー

PR 番号がない場合は `gh pr diff` をスキップし、ローカル git diff を使う。
base branch がない場合は upstream を優先し、なければ `main` とする。

## Procedure

以下の順序で実施する。

1. `git status --short --branch`
2. `git diff --stat`
3. `ruff check .`
4. `pytest`
5. 4 観点チェック（下記 Review Axes を参照）
6. Output Format に沿った報告

各ステップの失敗は停止せず記録し、全ステップ完了後に一括報告する。
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
`issue_ref` を使って対象 Issue の内容を参照する。

### 3) Migration Awareness

破壊的変更や移行説明が必要な差分かを確認し、説明不足を報告する。

### 4) Docs-Impl Consistency

ドキュメント記述と実装差分の意味が一致しているかを確認する。

## Output Format

出力は PR コメントにそのまま貼れる Markdown とし、以下の見出し構造を維持する。
（canonical との互換を保つため、見出し名・出力順は変更しない）

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
失敗がある場合は各項目に以下を含める。

- `Failure`: 失敗概要
- `Repro`: 再現コマンド
- `Likely Cause`: 原因候補

## Next Step

修正指示は書かず、委譲先のみを 1 行で書く。

- 失敗あり: `修正は別 skill（minimal-safe-impl など）へ委譲。review-preflight は報告のみ。`
- 失敗なし: `レビュー開始可。`

## Constraints

- 修正を行わない（本 skill は検査と報告のみ）
- push しない
- 外部 web 検索・任意リモートコンテンツへのアクセスをしない
- 破壊的操作をしない
- `ruff` / `pytest` の失敗時に自動修正・再試行ループをしない
- 報告は `Summary / Preflight Checks / Failures / Next Step` の順で出力する

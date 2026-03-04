# review-preflight

`docs/CODEX_RUNBOOK.md` のレビュー開始前チェック部分を、Codex CLI 向けの固定テンプレとして切り出した skill。
コマンド順序と出力見出しは runbook を正本とし、この文書ではレビュー前チェックの最小契約だけを定義する。

## Purpose

レビュー開始前の安全確認を固定する。

## Input

- PR 番号（任意）
- base branch（例: `main`）
- 現在の作業ツリー

## Fixed Procedure

以下のコマンドを必ずこの順序で実行する。省略、並べ替え、別コマンドへの置き換えはしない。

```bash
git status --short --branch
git diff --stat
ruff check .
pytest
```

詳細な位置づけと停止条件は `docs/CODEX_RUNBOOK.md` を参照する。この skill は runbook 全体の代替ではなく、レビュー開始前チェック部分のテンプレである。

## Failure Handling

失敗した場合は、各チェックを 1 つずつ分類して扱う。

1. 失敗した項目を分類する
2. 最小修正で閉じるなら `Next Step` を 1 行で提案する
3. 設計変更が必要なら停止理由を書く

`ruff` または `pytest` が失敗した場合、`Next Step` は必ず出力する。

## Output Format

出力は PR コメントにそのまま貼れる Markdown とし、3 回実行しても同じ見出し構造を維持する。
必ず以下の見出しをこの順序で出力する。

## Summary

短い結果サマリー

## Preflight Checks

- `git status`: `PASS` / `FAIL`
- `git diff`: `PASS` / `FAIL`
- `ruff`: `PASS` / `FAIL`
- `pytest`: `PASS` / `FAIL`

## Failures

失敗したチェックの詳細。失敗がない場合も `None` と明記する。

## Next Step

最小修正を 1 行で書く。停止が必要な場合は停止理由を 1 行で書く。失敗がない場合はレビュー開始可否を 1 行で書く。

---
name: issue-project-meta
description: issue-create 完了後に、Projects の列・優先度・依存関係を反映する手順を標準化する。Status/Priority 更新・blocked-by/sub-issue 追加・根拠記録・未実施時 TODO 記録を担う。
argument-hint: "[issue-url issue-number owner/repo project-number [blocked-by] [sub-issues]]"
disable-model-invocation: true
---

# issue-project-meta（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/CODEX_RUNBOOK.md`](../../../docs/CODEX_RUNBOOK.md) Appendix E
> 振る舞い・Rules・Procedure・Output テンプレは正本を参照してください。
> このファイルには Claude 固有の呼び出し構文と引数だけを記載します。

## Claude 固有の呼び出し

- 入力は `$ARGUMENTS`（`issue-create` Output B の引き渡し情報 + project_number）
- 開始前に必ず正本を読み、Rules に従う
- 正本を読む前にコマンドを出力してはならない
- 実際のコマンド実行はしない（コマンド案の生成のみ）

## Invocation Examples

- `/issue-project-meta "issue_url: https://github.com/wakadorimk2/personal-mcp-core/issues/106 issue_number: 106 owner: wakadorimk2 repo: personal-mcp-core project_number: 1"`
- `/issue-project-meta "issue_url: ... blocked_by: 104 sub_issues: 107"`

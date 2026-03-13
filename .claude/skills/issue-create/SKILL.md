---
name: issue-create
description: issue-draft で確定した title/body・ラベル候補・owner/repo を受け取り、gh label list によるラベル確認・重複チェック・gh issue create コマンド生成・作成結果記録の手順を標準化する。Projects/relationship メタデータ更新は issue-project-meta に委譲する。
argument-hint: "[issue-draft-output-or-title body labels owner/repo]"
disable-model-invocation: true
---

# issue-create（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/CODEX_RUNBOOK.md`](../../../docs/CODEX_RUNBOOK.md) Appendix D
> 振る舞い・Rules・Procedure・Output テンプレは正本を参照してください。
> このファイルには Claude 固有の呼び出し構文と引数だけを記載します。

## Claude 固有の呼び出し

- 入力は `$ARGUMENTS`（`issue-draft` Output A/B の確定済みデータ + ラベル候補 + owner/repo）
- 開始前に必ず正本を読み、Rules に従う
- 正本を読む前にコマンドを出力してはならない
- 実際のコマンド実行はしない（コマンド案の生成のみ）

## Invocation Examples

- `/issue-create "title: add issue-create skill / labels: documentation / repo: wakadorimk2/personal-mcp-core"`
- `/issue-create "issue-draft output: ## Goal ..."`

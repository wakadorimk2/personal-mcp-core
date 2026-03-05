---
name: issue-draft
description: clarify-request の確定済み構造化メモ（Output B）を受け取り、Goal/Scope/AC/Non-goal を含む GitHub Issue 草案 Markdown と title/body 最小セットを生成する。clarify 未完了時は生成拒否。
argument-hint: "[clarify-request-output-b]"
disable-model-invocation: true
---

# issue-draft（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/skills/issue-draft.md`](../../../docs/skills/issue-draft.md)
> 振る舞い・Rules・Procedure・Output テンプレは正本を参照してください。
> このファイルには Claude 固有の呼び出し構文と引数だけを記載します。

## Claude 固有の呼び出し

- 入力は `$ARGUMENTS`（`clarify-request` Output B の構造化メモ）
- 開始前に必ず正本を読み、Rules に従う
- 正本を読む前に草案を出力してはならない

## Invocation Examples

- `/issue-draft "## Clarify Result [DRAFT] ..."`
- `/issue-draft "Goal: issue-draft skill を定義する / Scope: ..."`

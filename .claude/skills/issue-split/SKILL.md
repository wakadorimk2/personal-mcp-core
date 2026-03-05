---
name: issue-split
description: issue-draft で草案化した大きな Issue を独立して完了判定できる子 Issue に分割し、依存関係を DAG（有向非巡回グラフ）として Markdown で表現する。issue-draft 後のオプション手順。人間の明示的な「分割が必要」の判断がある場合にのみ実行する。
argument-hint: "[issue-draft-output-a parent-title [split-hint]]"
disable-model-invocation: true
---

# issue-split（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/skills/issue-split.md`](../../../docs/skills/issue-split.md)
> 振る舞い・Rules・Procedure・Output テンプレは正本を参照してください。
> このファイルには Claude 固有の呼び出し構文と引数だけを記載します。

## Claude 固有の呼び出し

- 入力は `$ARGUMENTS`（`issue-draft` Output A の確定済み草案 Markdown + 親タイトル + 任意の分割ヒント）
- 開始前に必ず正本を読み、Rules に従う
- 正本を読む前に分割案を出力してはならない
- 人間が「分割が必要」と明示していない場合は分割を推奨・実行しない
- 実際の Issue 作成はしない（分割案の生成のみ）

## Invocation Examples

- `/issue-split "## Goal\n大きな機能を... / parent-title: add large-feature"`
- `/issue-split "issue-draft output: ## Goal ... / split-hint: 実装フェーズ別に分ける"`

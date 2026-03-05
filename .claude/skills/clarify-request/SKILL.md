---
name: clarify-request
description: Issue 作成前に目的・制約・優先順位を人間への質問で確定する。推測で埋めず、未確定は再質問する。実装案・結論の先出し禁止。
argument-hint: "[要求の断片・口頭メモ・issue-url]"
disable-model-invocation: true
---

# clarify-request（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/skills/clarify-request.md`](../../../docs/skills/clarify-request.md)
> 振る舞い・Rules・Procedure・Output テンプレは正本を参照してください。
> このファイルには Claude 固有の呼び出し構文と引数だけを記載します。

## Claude 固有の呼び出し

- 入力は `$ARGUMENTS`（要求の断片 / 口頭メモ / URL / issue番号のいずれか）
- 開始前に必ず正本を読み、Rules に従う
- 正本を読む前に質問・提案・実装案を出してはならない

## Invocation Examples

- `/clarify-request "ユーザーが過去のイベントを検索できるようにしたい"`
- `/clarify-request 103`
- `/clarify-request "Slackからのイベント自動取り込みを追加したい（詳細未定）"`

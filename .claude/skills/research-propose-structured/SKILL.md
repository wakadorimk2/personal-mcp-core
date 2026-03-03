---
name: research-propose-structured
description: 調査・比較・提案を"結論先出し"で構造化して返す。実装はしない（コードは疑似コードまで）。
argument-hint: "[topic-or-constraints-or-issue-url]"
disable-model-invocation: true
---

# research-propose-structured（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/skills/research-propose-structured.md`](../../../docs/skills/research-propose-structured.md)
>
> 振る舞い・Rules・Procedure・Output テンプレは正本を参照してください。
> このファイルには Claude 固有の呼び出し構文と引数だけを記載します。

---

## Claude 固有の呼び出し

- 入力は `$ARGUMENTS`（テーマ/制約/URL/issue番号のいずれか）
- 調査開始前に必ず正本を読む

## Invocation Examples

- `/research-propose-structured "Compare approaches to add a new adapter (constraints: low effort, reversible, python)"`
- `/research-propose-structured 25`
- `/research-propose-structured https://github.com/wakadorimk2/personal-mcp-core/issues/25`

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
> Mission / Rules / Output テンプレは正本を参照してください。
> このファイルには Claude 固有の制約・呼び出し方法のみ記載します。

---

## Claude 固有の制約

- 入力は `$ARGUMENTS`（テーマ/制約/URL/issue番号のいずれか）
- 必要なら issue / ドキュメントを読んでから整理する
- 足りない情報は「仮定/未確定」として明記し、条件付きで提案する

## Invocation Examples

- `/research-propose-structured "Compare approaches to add a new adapter (constraints: low effort, reversible, python)"`
- `/research-propose-structured 25`
- `/research-propose-structured https://github.com/wakadorimk2/personal-mcp-core/issues/25`

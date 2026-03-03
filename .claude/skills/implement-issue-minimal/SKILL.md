---
name: implement-issue-minimal
description: GitHub Issueをスコープ厳守で実装し、最小テストまで回して、diffとコミット案までを一括で出す。実装依頼のときに使う（自動実行はしない）。
argument-hint: "[issue-url-or-number]"
disable-model-invocation: true
---

# implement-issue-minimal（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/skills/implement-issue-minimal.md`](../../../docs/skills/implement-issue-minimal.md)
>
> Mission / Rules / Output テンプレは正本を参照してください。
> このファイルには Claude 固有の制約・呼び出し方法のみ記載します。

---

## Claude 固有の制約

- 入力は `$ARGUMENTS`（issue番号またはURL）
- まず `gh issue view` などで本文（Goal/Scope/完了条件）を取得してから進める
- 仮定が必要な場合: 破壊的変更になり得るなら中断して理由を述べる

## Invocation Examples

- `/implement-issue-minimal 25`
- `/implement-issue-minimal https://github.com/wakadorimk2/personal-mcp-core/issues/25`

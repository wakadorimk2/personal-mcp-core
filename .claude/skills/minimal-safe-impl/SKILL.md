---
name: minimal-safe-impl
description: Repo の MVP 互換性ポリシーに従って issue や実装依頼を最小差分で実装する。既存構造と CLI パターンを踏襲し、投機的リファクタや恒久互換レイヤを入れないときに使う。
argument-hint: "[issue-url-or-number-or-implementation-request]"
disable-model-invocation: true
---

# minimal-safe-impl（Claude アダプタ）

> このファイルは Claude Code 用のアダプタです。
> **正本（AI非依存）**: [`docs/skills/minimal-safe-impl.md`](../../../docs/skills/minimal-safe-impl.md)
> 振る舞い・Rules・Procedure・Output テンプレは正本を参照してください。
> このファイルには Claude 固有の呼び出し構文と引数だけを記載します。

## Claude 固有の呼び出し

- 入力は `$ARGUMENTS`（issue番号 / URL / 実装依頼文）
- 実装前に必ず正本を読む

## Invocation Examples

- `/minimal-safe-impl 15`
- `/minimal-safe-impl "Implement issue #15 following repo conventions."`
- `/minimal-safe-impl "Apply a minimal fix respecting the MVP compatibility policy."`

# Storage Unification Plan (#185)

Issue: <https://github.com/wakadorimk2/personal-mcp-core/issues/185>

## Purpose

`events.db` / `events.jsonl` の参照先非対称を解消し、`today` / `summary` / Web入力 / CLI が同一ストレージを参照する状態へ段階的に移行する。

## Decision Record (locked on 2026-03-08)

- 目標方針: C（#185 で方針確定後に計画的に単一化）
- 正本候補の最終案: `events.db`
- 移行期間中の真実源: `events.db`
- 移行期間中の `events.jsonl`: 互換レイヤ
- 実装順序: #189 -> #190 -> #191

## Current state (2026-03-08)

- CLI (`event-add` / `event-list` / `event-today`) は `events.jsonl` を read/write する
- Web入力 (`web-serve` の `/events` / `/events/ui`) は `events.db` に write する
- summary (`summary-generate` / dashboard 集計) は `events.db` を read/write する

注記: 現状は「非対称参照」であり、まだ dual-write ではない。

## Phased migration plan

1. Phase1 (#185): 方針と運用ルールを確定し、Decision Record を固定する
2. Phase2 (#189): storage abstraction を導入し、read/write 境界を統一する
3. Phase3 (#190): `db <-> jsonl` 相互再生成 migration tool を追加する
4. Phase4 (#191): dual-write/互換経路を撤去し、単一ストレージ運用に統一する

## Dual-write removal conditions

- 同一 `DATA_DIR` で Web入力イベントが `today` に即時反映される
- 同一 `DATA_DIR` で CLI `event-add` イベントが Web/summary から確認できる
- `today` / `summary` / Web入力 が同一ストレージを参照する
- migration tool の dry-run と復旧手順が検証済みである
- README / runbook の運用ルールが単一化後の状態に更新済みである

## Failure recovery rule (during transition)

- 真実源は `events.db` とする
- `events.jsonl` 欠損時は `events.db` から再生成する
- `events.db` 欠損時は `events.jsonl` から再生成できる手順を維持する
- 不一致検出時は `events.db` を優先し、差分を記録したうえで再生成する

## Follow-up issues

- #189: <https://github.com/wakadorimk2/personal-mcp-core/issues/189>
- #190: <https://github.com/wakadorimk2/personal-mcp-core/issues/190>
- #191: <https://github.com/wakadorimk2/personal-mcp-core/issues/191>

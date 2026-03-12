# Heatmap Density Audit

Issue #354 向けの `shipped_density` 分布監査方針。

## Policy

- 主分析窓は `last 365 days` を使う
- `all-time` は最古の real data 日からの参考値として併記する
- 色スケール判断は 365 日窓を優先し、all-time は sanity check としてだけ使う
- `p95/p75 >= 3` や `max/p90 >= 5` は heuristic signal であり、決定ルールではない

## Rationale

- Issue #354 の目的は 365-day heatmap UI の scale calibration なので、主分布は実表示窓に合わせる
- 初期の sparse period を all-time の主判断に使うと、現在の density を過小評価しやすい
- outlier flag は fixed threshold の脆さを示す補助線であって、repo の invariant ではない

## Command

```bash
PYTHONPATH=src python -m personal_mcp.server heatmap-density-audit --json --data-dir <DATA_DIR>
```

## Output Contract

- `primary_window`: 主結論に使う 365 日窓
- `all_time_reference`: 最古 real data 日からの参考窓
- `heuristic_flags.advisory_only = true`: 閾値フラグは補助情報

## Notes

- `earliest_real_data_date` は `domain != "summary"` の最古 local day を使う
- `all_time_reference` は pre-history を含めず、実データ開始前の空白日は混ぜない
- `/api/heatmap` と `/api/heatmap/debug` の semantics は変更しない
- 実測 snapshot: `docs/heatmap-density-audit-2026-03-12.md`

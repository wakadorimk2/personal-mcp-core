# Heatmap Density Audit Snapshot (2026-03-12)

Issue `#354` 向けの実測 snapshot。

## Dataset

- audit date: `2026-03-12` JST
- data dir: `PERSONAL_MCP_DATA_DIR`
- primary window: `last 365 days` (`2025-03-13` .. `2026-03-12`)
- all-time reference window: earliest real data day (`2026-03-08` .. `2026-03-12`)
- shipped population: `domain != "summary"` and `source != "web-form-ui"`

## Command

```bash
PYTHONPATH=src python -m personal_mcp.server heatmap-density-audit --json --data-dir "$PERSONAL_MCP_DATA_DIR"
```

## Recorded Stats

| window | total_days | zero_days | zero_day_ratio | min | p50 | p75 | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| primary `last_365_days` | 365 | 360 | 0.9863 | 0 | 0 | 0 | 0 | 0 | 41 |
| secondary `all_time_from_earliest_real_data` | 5 | 0 | 0 | 7 | 25 | 30 | 36.6 | 38.8 | 41 |

## Non-zero Days In Primary Window

| date | raw_count | telemetry_count | shipped_density |
|---|---:|---:|---:|
| 2026-03-08 | 66 | 36 | 30 |
| 2026-03-09 | 123 | 82 | 41 |
| 2026-03-10 | 77 | 58 | 19 |
| 2026-03-11 | 125 | 100 | 25 |
| 2026-03-12 | 37 | 30 | 7 |

## Interpretation

- `last 365 days` is the correct primary calibration window for the shipped UI, but the current dataset is too young to use those percentiles directly: `p50` through `p95` are all `0` because only 5 of 365 days are non-zero.
- The all-time reference window is short, but it reflects the actual active data range shown by the current product more honestly than the sparse 365-day percentiles.
- Upper-tail concentration does not currently look dominated by a single pathological outlier. `p95/p75 = 1.29` and `max/p90 = 1.12`, both well below the advisory thresholds.

## Input For #257

- Tuned fixed thresholds still look viable for the current dataset because the active 5-day range sits in a relatively narrow band (`7` to `41`) without a spike-shaped tail.
- A purely percentile-derived scale from the current 365-day window would collapse to zeros and would not be a useful basis for bucket design today.
- For the next step under `#257`, it is more defensible to prefer a distribution-aware calibration input anchored on the active-data window, while still keeping the shipped display window at 365 days.


# Heatmap Scale Decision

Issue `#257` 向けの shipped heatmap bucket / scale decision record。

## Decision

- 採用案: tuned fixed thresholds
- empty bucket は filled bucket と分離して扱う
- visual levels は `0..4` の 5 段階に固定する

## Bucket Contract

| bucket | shipped_density range | meaning |
|---|---:|---|
| 0 | `0` | empty / quiet day |
| 1 | `1..4` | light activity |
| 2 | `5..9` | visible activity |
| 3 | `10..19` | clearly active |
| 4 | `20+` | dense day |

## Why Fixed Thresholds

- `last 365 days` は shipped UI の calibration window として正しいが、2026-03-12 snapshot では `p50` から `p95` までが `0` に潰れており、percentile-derived scale の主根拠としては使えない
- active data window (`2026-03-08` .. `2026-03-12`) の `shipped_density` は `7..41` に収まり、単一 outlier に支配されていない
- そのため、現時点では dataset 依存の再計算より stable fixed buckets のほうが `#355` と `#356` の source of truth として扱いやすい

## Downstream Contract

- `#355` はこの bucket contract を shared mapping layer の正本として実装する
- `#356` は bucket index `0..4` を前提に palette / visual token を定義する
- color token 自体はこの文書では決めない

## References

- `docs/heatmap-density-audit-2026-03-12.md`
- `docs/heatmap-density-audit.md`
- `docs/heatmap-state-density-spec.md`
- `src/personal_mcp/tools/heatmap_scale.py`

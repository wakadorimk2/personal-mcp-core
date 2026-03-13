# Heatmap Metric Derivation Spec

> Scope: Issue #407 - source normalization and shipped density derivation
> Status: draft
> Role: source of truth for the metric-side pipeline that sits before bucket mapping, palette, and UI rendering

---

## 1. Purpose

This document defines the metric-side baseline and future derivation seam for the shipped heatmap.

Step 1 of Issue #407 fixes the current shipped semantics first, before comparing normalization or introducing a future derived metric.

This step does not change `/api/heatmap`.

---

## 2. Current Shipped Baseline

The current shipped heatmap metric is `shipped_density`.

Per local date, the shipped count is:

```text
shipped_density[date] = count(events WHERE
    local_date(ts) == date
    AND domain != "summary"
    AND source != "web-form-ui"
)
```

This is the current `display_population`.

Operationally, `/api/heatmap` returns the last local 28 days, including zero-value days, as:

```json
[{ "date": "YYYY-MM-DD", "count": N }]
```

Current implementation reference:

- `src/personal_mcp/tools/daily_summary.py::count_events_by_date`
- `docs/heatmap-state-density-spec.md` Section 2 and Section 3

---

## 3. Included And Excluded Populations

### Included in current shipped heatmap

- user-authored non-summary events
- events that belong to the current shipped observation surface

### Excluded from current shipped heatmap

- `domain == "summary"`
  - daily summary artifacts
  - derived data, not primary observation input
- `source == "web-form-ui"`
  - UI telemetry
  - system-generated interaction records

This exclusion fixes the current shipped heatmap as an observation-first surface rather than a raw activity counter.

---

## 4. Debug Boundary

The following fields are debug or verification surfaces and are not the shipped primary metric:

- `raw_count`
- `telemetry_count`
- `life_count`

`/api/heatmap/debug` may expose these values for verification, but Step 1 keeps them outside the shipped baseline contract.

In other words:

- shipped surface: `shipped_density`
- debug surface: raw and comparison-oriented breakdowns

---

## 5. What Step 1 Does Not Decide

Step 1 intentionally does not decide any of the following:

- source-family normalization strategy
- weighting across source families
- compression or cap policy
- future normalized metric naming
- bucket thresholds
- palette behavior
- temporal aggregation policy
- history navigation or summarized rendering semantics

Those belong to later steps in Issue #407 or to downstream issues such as `#355`, `#408`, and UI-track issues.

---

## 6. Why This Baseline Must Be Fixed First

The current dataset already shows a large gap between raw activity volume and shipped observation value.

As of the 2026-03-12 audit snapshot:

- the primary 365-day window contains 360 zero days
- only 5 days are currently non-zero
- non-zero shipped density values range from 7 to 41

This is enough to justify a future normalization discussion, but not enough reason to blur the meaning of the current shipped metric.

Step 1 therefore treats current shipped semantics as a fixed baseline that later design steps can compare against.

---

## 7. Step 2 - Source Family Inventory And Scale Gap

Current shipped semantics flatten multiple source families into one per-day count.

That is acceptable as a baseline, but it hides a meaningful scale gap between families.

### 7.1 Current source families relevant to heatmap design

| family | representative source/domain | current shipped treatment | scale characteristic | design risk |
|---|---|---|---|---|
| manual life logging | `source="web-form"` across `mood`, `general`, `worklog`, `eng` | included | low-frequency, human-authored, semantically dense | quiet days can look too empty if renderer expects GitHub-like volume |
| GitHub-derived eng activity | `source="github"` in `eng` domain | included | bursty, can produce many same-day events from one work stream | active engineering days can dominate the scale if treated like manual logs |
| UI telemetry | `source="web-form-ui"` | excluded from shipped, visible in debug | mechanically amplifies one human action into multiple records | would distort observation if allowed into shipped density |
| summary artifacts | `domain="summary"` | excluded from shipped | derived, not primary observation | would double-count interpretation output as activity |

### 7.2 Why the scale gap matters

The issue is not only telemetry noise.

Even after excluding telemetry and summary artifacts, the shipped population still mixes at least two included families with different behavior:

- manual life logging tends to be sparse but high-signal
- GitHub-derived `eng` events can arrive in bursts and cluster on a small number of active days

This means a single raw per-day count can over-represent families that naturally emit more events.

### 7.3 Evidence available today

The current audit snapshot already shows a concentrated active range:

- 360 zero days in the primary 365-day window
- 5 non-zero days in the current active data range
- non-zero `shipped_density` between 7 and 41

That snapshot is still too young to finalize normalization weights, but it is sufficient to justify separating source-family discussion from renderer-only tuning.

### 7.4 Step 2 decision

Issue `#407` should treat source-family scale gap as a metric-layer problem, not as a renderer-local palette problem.

This step does not yet decide how to normalize those families.
It only fixes the problem statement:

- raw daily counts are not source-neutral
- telemetry exclusion alone does not solve source-family skew
- a future derivation step must be able to distinguish family-level behavior before bucket mapping

---

## 8. Downstream Implications

### For `#355`

`#355` should treat current `shipped_density` semantics as a fixed input meaning until Issue `#407` defines a successor normalized input contract.

### For `#360`

`#360` can compare raw, shipped, and future normalized views, but should not redefine the shipped baseline here.

### For `#408`

`#408` may assume a daily metric input exists, but should not redefine the current shipped observation population.

---

## 9. Decision Summary For Step 1 And Step 2

- keep current `/api/heatmap` semantics fixed as the baseline
- treat current shipped heatmap as `display_population`, not raw activity count
- keep debug metrics outside the shipped baseline contract
- treat source-family scale gap as a metric-layer problem that remains unsolved in the current baseline
- postpone normalization and derivation design to later steps of `#407`

---

## 10. References

- `docs/heatmap-state-density-spec.md`
- `docs/heatmap-density-audit-2026-03-12.md`
- `docs/mvp-contract-decisions.md`
- `docs/eng-domain-concept.md`
- `src/personal_mcp/tools/daily_summary.py`
- `src/personal_mcp/tools/log_form.py`
- Issue `#407`
- Issue `#355`
- Issue `#360`
- Issue `#408`

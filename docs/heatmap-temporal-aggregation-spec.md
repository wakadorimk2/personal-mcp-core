# Heatmap Temporal Aggregation Spec

> Scope: Issue #408 — resolution-aware aggregation policy for temporal zoom
> Status: draft
> Role: metric-side aggregation contract consumed by #391 (history navigation UI)

---

## 1. Purpose

This document defines the temporal aggregation policy that sits between the daily metric pipeline and the UI rendering layer.

Issue #407 fixed how per-day metrics are derived from source-family events.
This document defines what happens when those daily values need to be aggregated across different time ranges.

The output is a contract that:

- #391 (history navigation UI) can consume without redesigning aggregation logic
- downstream metric work can extend without reopening source-family normalization
- temporal zoom support can be built on through an explicit future-state range contract

This document defines a future-state contract.
It does not retroactively change the current shipped `/api/heatmap` baseline, which still returns the last local 28 days, and it does not implement anything.

---

## 2. Pipeline Position

Issue #407 defined the metric pipeline as:

```text
source daily aggregates
-> family-level normalization
-> optional post-normalization compression/cap
-> derived heatmap-ready value (per day)
-> bucket mapping contract (#355)
-> palette / UI consumers
```

This document adds one step between daily derivation and bucket mapping:

```text
derived heatmap-ready value (per day)
-> range aggregation (defined in this document)
-> range-aware metric value (per aggregation period)
-> bucket mapping contract (#355)
-> palette / UI consumers
```

Range aggregation is a distinct layer.
It does not alter how per-day values are derived.
It only defines how per-day values are combined into coarser representations when the rendering range is wider than one day.

---

## 3. Range Definitions

### 3.1 Three-range model

The policy defines three named ranges:

| range | name | default coverage | metric resolution |
|---|---|---|---|
| near | primary view | most recent 6 weeks | daily |
| mid | mid history | weeks 7 through 52 from today | weekly |
| far | far history | month 13 and beyond from today | monthly |

Coverage values are policy defaults, not hard-coded constants.
They may be adjusted by implementation without revisiting this document, as long as the range ordering (near < mid < far) and resolution hierarchy (daily > weekly > monthly) are preserved.

### 3.2 Boundary rationale

The current shipped baseline remains the 28-day `/api/heatmap` contract defined in `docs/heatmap-metric-derivation-spec.md`.

Within the future-state contract defined here, the near boundary is the most recent 42 days (6 weeks) at daily resolution.
That future-state boundary should not be changed by #408 or #391 without reopening this policy.

The mid/far boundary at month 12 is a policy default chosen for two reasons:

- one full year of mid-range weekly resolution covers approximately 46 weeks, which is compact enough to display without overflow
- beyond one year, monthly resolution is sufficient for assurance-mirror intent without overloading the observer

### 3.3 Range identity semantics

Each range is a named, stable identity from the perspective of the consumer.

A consumer (such as #391) may request data for a given range by name.
The metric layer responds with aggregated values whose resolution matches the range definition.
Consumers must not assume daily resolution for mid or far range responses.

---

## 4. Aggregation Semantics

### 4.1 What aggregation is

Aggregation in this policy means: combining daily metric values within a window period into one representative value per period.

For mid range, one representative value per week.
For far range, one representative value per month.

### 4.2 Aggregation operator

This policy recommends **mean daily value** (arithmetic average) as the primary aggregation operator for both mid and far ranges.

```text
aggregated_value[period] = mean(derived_daily_value[day] for day in period)
```

Zero-value days within the period are included in the denominator.
This preserves the observation that a period had sparse activity.

### 4.3 Why mean over other operators

| operator | behavior | issue for assurance-mirror use |
|---|---|---|
| sum | grows with period width | mid and far cells are not comparable to near (daily) cells; burst week looks similar to sustained week |
| max | shows peak only | hides total sparse activity; one active day dominates the whole week or month |
| mean daily value | maintains per-day scale | mid weekly cell and near daily cell remain in the same numeric range; sparse periods show proportionally lower values |
| presence count | counts active days per period | loses density information; all active-day periods look equivalent |

Mean daily value is preferred because:

- it preserves comparability across near/mid/far: a cell with value X means "approximately X events per day on average in this period" regardless of whether the period is a day, a week, or a month
- it is honest about sparse periods: a week with 1 active day at value 7 yields a weekly mean of 1.0, not 7
- it does not require scale recalibration when navigating between ranges

### 4.4 Non-integer values

Mean aggregation may produce non-integer values for mid and far ranges.

Downstream consumers (bucket mapping in #355) must accept non-integer inputs.
Rounding policy is left to the implementation and does not need to be decided here.

### 4.5 Zero-value representation

Periods where all days have zero derived value produce an aggregated value of 0.

Periods with missing data (no event records at all for that day) are treated as zero for aggregation purposes.
This is consistent with the current near-range behavior of `/api/heatmap`, which includes zero-value days.

---

## 5. Why Daily Raw Grid Is Not Forced for Older History

### 5.1 The problem with forcing daily resolution everywhere

Retaining daily raw data and returning daily cells for far history creates two problems:

- display cost grows linearly with history length (10 years = 3,650 cells)
- daily cells in far history contain more noise than signal; most will be zero for sparse data like this dataset

### 5.2 What is retained

Event records remain append-only and immutable.
Daily derived values can always be recomputed from the stored event records.

This policy does not require discarding or pre-aggregating raw data.

### 5.3 What changes at the display layer

The metric layer returns different granularity depending on the range requested:

- for near range: one value per day (42 values)
- for mid range: one value per week (approximately 46 values for a 52-week window)
- for far range: one value per month (number depends on history depth)

The UI (via #391) renders cells at the appropriate granularity for the requested range.
It does not need to force daily cells for mid or far ranges.

### 5.4 Condition under which daily grid is not forced

Daily raw grid is not required for older history when:

1. the range is outside the near boundary (beyond 6 weeks from today)
2. the consumer (UI or API) explicitly requests a mid or far range
3. the aggregated response shape reflects the correct period resolution

Older history may still be accessed at daily resolution for debug or inspection purposes,
but shipped UI rendering is not required to present it that way.

---

## 6. Isolation From #391

This document defines aggregation policy only.
The following are explicitly out of scope and remain with #391:

- navigation UI design (how the user moves between near/mid/far)
- how the current visible range is displayed to the user
- rendered cell shape, size, or density for mid/far cells
- mobile vs desktop layout for history navigation
- animation or transition behavior between ranges

#391 consumes the contract defined in Section 7.
It must not redefine aggregation operators or range boundaries.

---

## 7. Contract Consumed by #391

### 7.1 What #391 may assume

After this document is accepted, #391 may assume the following:

- a near range exists, covering the most recent 6 weeks at daily resolution
- a mid range exists, returning aggregated weekly values for older history up to approximately 12 months back
- a far range exists, returning aggregated monthly values for history beyond 12 months
- the aggregation operator for mid and far is mean daily value
- zero-value periods are represented as 0, not absent
- the per-period value for mid and far is numerically comparable with daily values in the near range

### 7.2 What #391 must not assume

- exact coverage boundaries (e.g., "exactly 46 weeks") — these are policy defaults subject to implementation
- that daily-resolution data is unavailable; it can still be retrieved for debug purposes
- that bucket thresholds are the same across ranges; bucket policy is #355's responsibility
- that this document defines how the API exposes the range interface

### 7.3 Interface boundary

The precise API shape (endpoint name, query parameter, response field names) for requesting mid and far range data is not defined here.
That is an implementation decision for when #391 begins implementation.

This contract defines the semantic invariants that the API must satisfy, not the wire format.

---

## 8. Metric-Layer Concerns Separated From #391

Issue #391 originally combined history navigation and summarized rendering.
This section records the metric-layer concerns that belong here rather than in #391.

| concern | belongs to | rationale |
|---|---|---|
| aggregation operator choice (mean vs sum vs max) | this document (#408) | metric-layer semantics, independent of UI layout |
| range boundary definitions (6 weeks, 52 weeks, etc.) | this document (#408) | policy defaults affecting what the metric layer returns, not how it is rendered |
| zero-value period inclusion in denominator | this document (#408) | affects the numeric meaning of mid/far cells |
| why daily grid is not forced for far history | this document (#408) | metric-side reason: scale and noise, not UI preference |
| how navigation UI looks | #391 | UI layer |
| how visible range is shown to user | #391 | UI layer |
| desktop / mobile layout for history | #391 | UI layer |

---

## 9. What This Document Does Not Decide

The following are explicitly deferred to other issues:

- **bucket boundaries and bucket count**: this is #355's responsibility
- **palette token mapping for mid/far cells**: UI epic
- **exact API shape for range requests**: implementation decision for #391 phase
- **whether far range is implemented in MVP**: shipping decision
- **source-family normalization**: defined by #407, not revisited here
- **inspection or debug surface for mid/far**: out of scope (#360 or similar)

---

## 10. Acceptance Mapping

| Issue #408 acceptance criterion | Where this document answers it |
|---|---|
| near / mid / far range ごとの aggregation contract が読める | Section 3, Section 4, Section 7 |
| older history を daily raw grid のまま強制しない条件が明記されている | Section 5 |
| `#391` から切り離すべき metric 論点が整理されている | Section 8 |
| temporal zoom / resolution change に耐える前提が明文化されている | Section 3.3, Section 4.3, Section 7.1 |

---

## 11. Decision Summary

- temporal aggregation is a distinct layer between daily metric derivation and bucket mapping
- three named ranges: near (daily, 6 weeks), mid (weekly, weeks 7–52), far (monthly, month 13+)
- range boundaries are policy defaults, not constants; range ordering and resolution hierarchy are invariants
- aggregation operator: mean daily value for mid and far ranges
- zero-value days are included in the mean denominator
- raw event records are always retained; aggregation is a display-layer concern, not a storage decision
- older history is not required to use daily grid resolution in shipped rendering
- #391 consumes the contract in Section 7 without redesigning aggregation
- bucket policy, palette, and API wire format are deferred to downstream issues

---

## 12. References

- `docs/heatmap-metric-derivation-spec.md` — upstream daily derivation contract (#407)
- `docs/heatmap-state-density-spec.md` — shipped_density baseline and observation layer definition
- `docs/heatmap-metric-derivation-spec.md` — current dataset snapshot and sparse-baseline evidence are absorbed there
- Issue #408 — scope and acceptance criteria for this document
- Issue #407 — daily metric derivation seam (upstream)
- Issue #391 — history navigation UI (downstream consumer)
- Issue #353 — top-level heatmap epic; recent-6-week primary view policy
- Issue #355 — shared bucket mapping contract (downstream)
- Issue #357 — recent-6-week primary view implementation (CLOSED)

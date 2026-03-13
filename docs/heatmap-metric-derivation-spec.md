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

## 8. Step 3 - Normalization Candidate Comparison

Step 3 compares candidate approaches for absorbing source-family skew before bucket mapping.

The purpose here is to narrow the design direction, not to freeze numeric coefficients.

### 8.1 Candidate comparison

| candidate | summary | pros | cons | Step 3 status |
|---|---|---|---|---|
| renderer-only adjustment | keep raw shipped counts and solve visibility only with palette or thresholds | minimal implementation churn | leaves source skew in the metric itself; repeats the same problem in every consumer | reject |
| hard source exclusion | exclude high-volume included families such as GitHub from shipped metric | simple and predictable | collapses meaningful `eng` observation into absence; too destructive for assurance mirror intent | reject |
| per-event weighting | assign source-family weights before daily aggregation | directly addresses family skew | exact weights become arbitrary too early; hard to explain or audit in current sparse dataset | keep as future sub-technique, not the primary contract |
| per-family daily normalization | aggregate by family first, then combine family-level daily signals into one derived value | preserves presence while reducing burst domination; creates a reusable seam before bucket mapping | needs explicit terminology and pipeline contract | prefer |
| compression or cap after daily count | compress daily counts with a cap, log-like curve, or bounded transform | reduces domination by extreme burst days | if applied after family mixing, it still hides which family caused the skew | secondary technique only, after family-level seam exists |

### 8.2 Direction chosen in Step 3

Step 3 prefers a two-layer direction:

1. keep current shipped baseline fixed for backward understanding
2. design future derivation around per-family daily normalization before bucket mapping

This does not yet fix:

- the list of final family groups
- any exact weighting numbers
- any exact compression formula

### 8.3 What Step 3 rejects

Step 3 explicitly rejects using UI palette or threshold tuning as the primary answer to source-family skew.

It also rejects dropping GitHub-derived `eng` activity from the shipped metric entirely, because the problem is disproportion, not irrelevance.

### 8.4 Step 3 decision

The derivation seam introduced by Issue `#407` should be able to represent:

- source-family daily aggregates
- a family-aware normalization step
- an optional post-normalization compression or cap step
- a final heatmap-ready value consumed by bucket mapping

The seam should not require the renderer to rediscover source-level behavior on its own.

---

## 9. Step 4 - Metric Pipeline Definition

Step 4 fixes the metric-side pipeline that converts source daily aggregates into a heatmap-ready value.

The goal is to separate responsibilities so downstream issues do not redefine the same logic in different layers.

### 9.1 Pipeline stages

| stage | output | responsibility | does not decide |
|---|---|---|---|
| A. source daily aggregates | per-day counts or signals grouped by source family | preserve source-family distinction before mixing | bucket boundaries, palette, UI layout |
| B. family-level normalization | comparable per-family daily signals | absorb family-specific scale differences | visual token count, temporal aggregation policy |
| C. optional post-normalization compression/cap | bounded or compressed daily signal | keep burst days from dominating the combined metric | source-family grouping itself |
| D. derived heatmap-ready value | one daily metric consumable by bucket mapping | provide a stable metric-side output contract | UI thresholds, legends, interaction behavior |

### 9.2 Canonical flow

The future metric-side flow should be read as:

```text
source daily aggregates
-> family-level normalization
-> optional post-normalization compression/cap
-> derived heatmap-ready value
-> bucket mapping contract (#355)
-> palette / UI consumers
```

### 9.3 Stage responsibilities

#### A. Source daily aggregates

This stage keeps raw daily input separated by family.

Examples:

- manual life logging daily signal
- GitHub-derived `eng` daily signal
- excluded telemetry and summary families retained only for debug comparison

#### B. Family-level normalization

This stage makes family outputs comparable enough to combine.

Its job is to answer:

- how a bursty GitHub day compares with a sparse manual day
- how family-specific volume should be reduced without erasing the presence of that family

#### C. Optional post-normalization compression or cap

This stage is explicitly optional.

It exists because even after family-aware normalization, some days may still be too dominant for a reassurance-oriented heatmap.

If used, it must run after family-level normalization, not instead of it.

#### D. Derived heatmap-ready value

This is the metric-side output that downstream issues consume.

It is not yet a bucket index and not a palette token.
It is the last numeric or ordinal value produced before `#355` maps it into shared buckets.

### 9.4 Step 4 decision

Issue `#407` defines the metric pipeline up to the derived heatmap-ready value.

It does not define:

- bucket boundaries or bucket count
- palette token mapping
- navigation or history rendering behavior
- near/far aggregation policy

Those remain with downstream issues.

---

## 10. Step 5 - Transition Seam Between Current And Future Metrics

Step 5 defines how later issues can introduce a future normalized metric without rewriting the meaning of the current shipped baseline.

### 10.1 Separation of roles

| term | role in Step 5 | notes |
|---|---|---|
| `shipped_density` | current shipped baseline metric | today’s `/api/heatmap` meaning; fixed for comparison |
| `display_population` | current shipped counting set | baseline population, not a future normalization algorithm |
| source daily aggregates | pre-mix family-level inputs | new internal seam for future derivation |
| derived heatmap-ready value | future metric-side output before buckets | successor input contract for `#355` |

### 10.2 Transition rule

Issue `#407` does not require the repository to immediately replace `shipped_density`.

Instead, it defines a transition seam:

- current shipped semantics remain the comparison baseline
- future metric work may add a derived heatmap-ready value behind a new contract
- bucket mapping should depend on that future contract once introduced
- debug or inspection flows may show both baseline and future-derived views side by side

### 10.3 What must not happen during transition

The transition should not:

- silently change the meaning of `/api/heatmap` while keeping the same terminology
- make UI consumers infer normalization rules from renderer-local thresholds
- collapse current baseline and future-derived contract into the same undefined term

### 10.4 Compatibility posture

At the design level, Step 5 assumes two different responsibilities:

- baseline semantics remain stable enough for comparison and migration reasoning
- future derivation contract can evolve as a metric-layer concern before UI decisions are revisited

That means later implementation should prefer an explicit seam over an in-place semantic rewrite.

### 10.5 Step 5 decision

Issue `#407` treats `shipped_density` as the baseline and a future derived heatmap-ready value as the successor contract.

The issue does not yet standardize the implementation path for exposing both at runtime.
It only fixes the conceptual boundary that downstream issues must respect.

---

## 11. Step 6 - Downstream Issue Contract

Step 6 records how other issues should consume the decisions made in `#407`.

### 11.1 Downstream responsibility matrix

| issue | consumes from `#407` | must not redefine | expected output |
|---|---|---|---|
| `#257` | background rationale for why raw daily counts are unstable across families | source-family normalization or derivation seam | bucket / scale decision record |
| `#355` | successor metric-side input contract before bucket mapping | source-family grouping logic, normalization rationale | shared bucket mapping contract |
| `#360` | baseline vs future-derived comparison boundary | shipped default metric or primary UX semantics | developer inspection support |
| `#408` | assumption that a daily metric input exists before range aggregation | source-family daily derivation semantics | near/far aggregation policy |

### 11.2 Specific impact notes

#### `#257`

`#257` remains the decision record for bucket and scale strategy.

Issue `#407` can explain why bucket decisions must not be mistaken for normalization, but it does not reopen bucket policy itself.

#### `#355`

`#355` should consume the metric-side output after derivation, not recreate derivation logic inside bucket mapping.

If `#355` needs input assumptions, it should reference:

- current baseline semantics for backward understanding
- future derived heatmap-ready value as the intended successor input

#### `#360`

`#360` is the correct place to compare:

- raw view
- current shipped baseline
- future normalized or derived view

But it should remain a validation surface, not the place where derivation meaning is created.

#### `#408`

`#408` works one layer later in the pipeline.

It may define how daily inputs are aggregated across near, mid, and far ranges, but it should consume the daily metric contract rather than redesign source-family normalization.
The accepted definition is in `docs/heatmap-temporal-aggregation-spec.md`.

### 11.3 Step 6 decision

Issue `#407` is the source of truth for metric-side daily derivation semantics before bucket mapping and range aggregation.

Downstream issues may consume that contract in different ways, but they should not fork its terminology or move derivation logic into UI or aggregation layers.

---

## 12. Step 7 - Acceptance Mapping And Follow-up Boundary

Step 7 makes this document usable as the completion artifact for Issue `#407`.

### 12.1 Acceptance mapping

| Issue `#407` acceptance criterion | Where this document answers it |
|---|---|
| raw source ごとの scale 差と問題点が明文化されている | Section 7 |
| derived metric への変換パイプラインが文章で固定されている | Section 9 |
| source normalization を renderer 側の調整で代替しない方針が明記されている | Section 8 |
| `#257` `#355` `#360` への影響範囲が読める | Section 11 |

### 12.2 Remaining work outside `#407`

This document intentionally leaves the following to other issues:

- exact bucket boundaries and bucket count -> `#257` and `#355`
- runtime implementation of the successor contract -> follow-up implementation work under `#355`
- developer comparison surface -> `#360`
- near / mid / far range aggregation semantics -> `#408`
- UI palette, interaction, detail, and history navigation -> UI epic issues under `#406`

### 12.3 Invariants fixed by `#407`

After this issue, downstream work should treat the following as fixed:

- current shipped baseline and future derived metric are different layers
- source-family skew is a metric-layer concern
- bucket mapping starts after metric derivation, not before it
- renderer-local tuning is not the primary answer to source-family skew

### 12.4 Step 7 decision

This document is intended to serve as the decision record for Issue `#407`.

Later issues may add implementation details or runtime surfaces, but they should not need to restate the core metric-derivation argument captured here.

---

## 13. Downstream Implications

### For `#355`

`#355` should treat current `shipped_density` semantics as a fixed baseline and move to the successor derived input only through an explicit shared contract.

### For `#360`

`#360` can compare raw, shipped, and future normalized views, but should not redefine the baseline or invent the successor contract itself.

### For `#408`

`#408` may assume a daily metric input exists, but should not redefine the current shipped observation population.

---

## 14. Decision Summary Through Step 7

- keep current `/api/heatmap` semantics fixed as the baseline
- treat current shipped heatmap as `display_population`, not raw activity count
- keep debug metrics outside the shipped baseline contract
- treat source-family scale gap as a metric-layer problem that remains unsolved in the current baseline
- prefer per-family daily normalization over renderer-only adjustment
- allow compression or cap only after a family-aware seam exists
- define a four-stage metric pipeline before bucket mapping and UI consumption
- separate the current baseline metric from the future derived successor contract
- treat `#407` as the source of truth for metric-side daily derivation semantics
- map the document directly to Issue `#407` acceptance criteria and follow-up boundaries

---

## 15. Current density audit evidence (2026-03-12)

The density audit policy and the 2026-03-12 dataset snapshot are absorbed here so that
the metric derivation baseline keeps its evidence without a separate standalone audit doc.

Policy used for calibration:

- use `last 365 days` as the primary analysis window
- keep `all-time` only as a reference window from the earliest real data day
- treat `p95/p75 >= 3` and `max/p90 >= 5` as advisory heuristics, not decision rules
- keep `/api/heatmap` and `/api/heatmap/debug` semantics unchanged while this evidence is used

Recorded snapshot (`2026-03-12` JST):

| window | total_days | zero_days | zero_day_ratio | min | p50 | p75 | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| primary `last_365_days` | 365 | 360 | 0.9863 | 0 | 0 | 0 | 0 | 0 | 41 |
| secondary `all_time_from_earliest_real_data` | 5 | 0 | 0 | 7 | 25 | 30 | 36.6 | 38.8 | 41 |

Non-zero days in the primary window:

| date | raw_count | telemetry_count | shipped_density |
|---|---:|---:|---:|
| 2026-03-08 | 66 | 36 | 30 |
| 2026-03-09 | 123 | 82 | 41 |
| 2026-03-10 | 77 | 58 | 19 |
| 2026-03-11 | 125 | 100 | 25 |
| 2026-03-12 | 37 | 30 | 7 |

Interpretation:

- `last 365 days` remains the shipped display window, but the current dataset is too young for percentile-derived thresholds because only 5 of 365 days are non-zero
- the short all-time reference window better reflects the currently active data range than the sparse 365-day percentiles
- upper-tail concentration does not currently look dominated by one pathological outlier; `p95/p75 = 1.29` and `max/p90 = 1.12`

## 16. References

- `docs/heatmap-state-density-spec.md`
- `docs/mvp-contract-decisions.md`
- `docs/eng-domain-concept.md`
- `src/personal_mcp/tools/daily_summary.py`
- `src/personal_mcp/tools/log_form.py`
- Issue `#407`
- Issue `#355`
- Issue `#360`
- Issue `#408`

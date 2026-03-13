# Heatmap v1 Density Semantics — Decision Record

> **スコープ**: Issue #312 — density semantics / telemetry boundary の固定
> **作成根拠**: Issue #253 で確定した heatmap 意味定義を、v1 の runtime / debug / color-scale follow-up が参照できる粒度へ operationalize する。
> **この文書の役割**: Issue #256（debug surface 実装）と #257（color scale 検討）の dependency / terminology source。
> **#407 との関係**: source normalization と future derivation seam は `docs/heatmap-metric-derivation-spec.md` を参照する。
> **変更禁止**: この文書の決定を覆す変更は Maintainer の明示承認が必要。

---

## 1. #253 との関係

Issue #253 は heatmap の density semantics を概念レベルで確定した **authoritative decision** である。

この文書はその上位決定を前提とし、以下を行う：

- v1 observation layer の操作的定義
- telemetry の扱い（比較と採否）
- `life_density` / `system_density` concept の採否
- debug 導線の定義
- #256 / #257 が参照できる terminology と dependency の固定

**#253 の内容を再議論しない。** この文書で引用する #253 の前提を覆す発見があった場合は、実装を止め Maintainer へエスカレーションする。

この文書が #253 から引き継ぐ固定前提は次の 4 点である。

- heatmap は raw event count の表示ではなく、`state change density` を可視化する UI である
- 観測は coarse / medium / fine の observation layer を持つ
- telemetry は通常の life view と別レイヤーで扱う
- 集約単位は universal metric へ固定せず、観測解像度や event kind に応じて自然な単位を採る

この要約と #253 本文の語義が衝突した場合は、#253 を優先する。

---

## 2. v1 Observation Layer

v1 shipped UI における observation layer を以下に固定する。

**採用: user-authored life events**

観測対象とするイベントの条件:

```
include event WHERE
    domain != "summary"
    AND source != "web-form-ui"
```

### 除外対象の整理

| 除外理由 | 識別条件 | 除外タイミング |
|---|---|---|
| 日次サマリー（派生データ） | `domain == "summary"` | 既実装（現在の `count_events_by_date`） |
| UI telemetry（システム生成） | `source == "web-form-ui"` | `#317` で実装済み |

### 実装反映状況

現在の `count_events_by_date`（`src/personal_mcp/tools/daily_summary.py:81`）は
`domain == "summary"` と `source == "web-form-ui"` の両方を除外し、
`/api/heatmap` はこの observation layer に一致する `shipped_density` を返している。

**実装変更禁止**: この文書は spec であり、`count_events_by_date` のコード変更は行わない。

---

## 3. v1 Shipped UI が表示する主指標

**primary metric: `shipped_density`**

定義:

```
shipped_density[date] = count(events WHERE
    local_date(ts) == date
    AND domain != "summary"
    AND source != "web-form-ui"
)
```

- 集計単位: ローカル日（timezone-aware）
- 集計期間: 直近 28 日（当日含む）
- データ形状: `[{date: "YYYY-MM-DD", count: N}]`（現在の `/api/heatmap` と同形）

この定義が `/api/heatmap` で返すべき v1 の意味定義。

**現在の実装**: `#317` 適用後の `/api/heatmap` は `shipped_density` を返している。

### 3.1 Population seam (Issue #332)

Issue #332 は heatmap semantics の再定義ではなく、legacy telemetry を scale 母集団から分離するための
data contract / aggregation seam を導入する issue として扱う。

この issue で導入する概念:

| term | meaning |
|---|---|
| `display_population` | shipped `/api/heatmap` が数える集合。#332 では変更しない |
| `scale_population` | 将来の scale-specific consumer が参照する調整用集合。#332 では seam のみ導入する |

追加方針:

- `data.observation_model` を optional metadata として導入する
- 新規 UI telemetry writer は `data.observation_model = "current"` を書く
- existing historical record は immutable のまま保持し、migration しない
- historical fallback は explicit boundary date ベースで扱う
- `source` や legacy payload shape から legacy/current を暗黙推定しない

非目標:

- `/api/heatmap` の response shape や shipped count semantics の変更
- `/api/heatmap/debug` に新しい field を追加すること
- `raw_count` / `shipped_density` の再定義
- relative scale の consumer や UI 色分け変更（#257 系で扱う）

---

### 3.1 Population seam (Issue #332)

Issue #332 は heatmap semantics の再定義ではなく、legacy telemetry を scale 母集団から分離するための
data contract / aggregation seam を導入する issue として扱う。

この issue で導入する概念:

| term | meaning |
|---|---|
| `display_population` | shipped `/api/heatmap` が数える集合。#332 では変更しない |
| `scale_population` | 将来の scale-specific consumer が参照する調整用集合。#332 では seam のみ導入する |

追加方針:

- `data.observation_model` を optional metadata として導入する
- 新規 UI telemetry writer は `data.observation_model = "current"` を書く
- existing historical record は immutable のまま保持し、migration しない
- historical fallback は explicit boundary date ベースで扱う
- `source` や legacy payload shape から legacy/current を暗黙推定しない

非目標:

- `/api/heatmap` の response shape や shipped count semantics の変更
- `/api/heatmap/debug` に新しい field を追加すること
- `raw_count` / `shipped_density` の再定義
- relative scale の consumer や UI 色分け変更（#257 系で扱う）

### `source` フィルタと `observation_model` / `boundary_date` の分担

`source != "web-form-ui"` と `data.observation_model` / `boundary_date` は、同じ問題を別の層で扱う。

| 仕組み | 役割 | この issue での扱い |
|---|---|---|
| `source != "web-form-ui"` | shipped `/api/heatmap` の `display_population` を定義する | #317 実装済み。#343 でも変更しない |
| `data.observation_model = "current"` | 新規 writer が current observation model に属することを明示する | metadata contract として保持する |
| `boundary_date` | historical records を scale 用の fallback で切り分ける | `scale_population` を絞る seam として使う |

設計上の関係:

- `display_population` は現行 shipped semantics のまま維持する
- `scale_population` は `display_population` を土台にしつつ、必要なら `boundary_date` でさらに狭める
- historical records の扱いは `source` や legacy payload shape から暗黙推定せず、明示的な boundary で制御する

そのため #343 は telemetry 除外ロジックを置き換える issue ではなく、
`source != "web-form-ui"` で決まる表示用集合に対して、
scale 用の母集団を別条件で扱えるようにする issue と位置づける。

---

## 4. Telemetry の扱い — 3案比較と採否

### 比較表

| 案 | 概要 | v1 採否 |
|---|---|---|
| **weight 0（exclude）** | telemetry を density から除外する | **採用** |
| **low weight** | telemetry に小さな重みを付けてカウントする | **不採用** |
| **separate density axis** | telemetry を別 density 軸で表示する | **不採用（debug 用途に保留）** |

### weight 0（exclude）を採用する根拠

1. **設計原則との整合**: telemetry events は UI インタラクション計測のための system-generated data であり、user activity の観測値ではない（`design-principles.md` 原則 2「Human Observability 基盤」）。
2. **ノイズ分離**: 1 件の user log 入力が 2〜3 件の telemetry events（`input_submitted` + `save_success` 等）を生成するため、telemetry を混入させると density が実際の活動量より過大に見える。
3. **実装単純性**: フィルタ条件が `source != "web-form-ui"` の 1 条件で表現できる。既存の summary 除外ロジックと同じ接線（observation layer の分離）で扱える。
4. **可逆性**: 除外したイベントは DB に保持される。debug 時には `raw_count` として参照可能。

### low weight を採用しない理由

- 重みの根拠（0.1 など）の設定が恣意的であり、design principles の「非評価的設計（non-evaluative design）」に反する。
- 小数カウントの実装は既存の integer count と API 互換でなくなるリスクがある。
- MVP の最小性・可逆性原則（CLAUDE.md）に適合しない。

### separate density axis を採用しない理由（v1 shipped UI）

- v1 shipped UI の scope を超える UI 変更を要する。
- color scale を 2 軸に分けることは「色スケールの最終設計」に踏み込むため、本 Issue のスコープ外（禁止）。
- ただし **debug surface 用途に保留**する（Section 6 参照）。#256 でこの軸を debug 導線として検討してよい。

---

## 5. `life_density` / `system_density` concept の採否

### 用語定義（概念レベル）

| term | 意味 |
|---|---|
| `life_density` | user-authored life events の density = `shipped_density` の concept 語 |
| `system_density` | system-generated events（summary + telemetry）の density |

### v1 での採否決定

**概念として採用、公開 interface は保留**

- `life_density` / `system_density` はこの spec および後続 #256 / #257 の **内部 terminology** として使用する。
- API レスポンスフィールド名・schema フィールド名としての **公式採用は v1 では行わない**。
- 公開 interface 化には Maintainer の明示承認と API contract 変更 Issue が必要（人間レビュー必須トリガー）。

### 保留理由の明記（再開条件）

- `life_density` を公開 interface とするには `/api/heatmap` のレスポンス shape を変更するか、新 endpoint を追加する必要がある。
- これは API contract / schema change であり、互換性ポリシー（`README.md#互換性ポリシー`）の審査対象。
- v1 期間中のフィールド名変更は禁止（`AI_GUIDE.md` 互換性ガードレール参照）。

---

## 6. Debug Surface — `raw_count` と `shipped_density` の比較

### 各値の定義

| 値 | 定義 | 現在の実装 |
|---|---|---|
| `raw_count` | summary 除外のみの日別件数 | `/api/heatmap/debug` の `raw_count` |
| `shipped_density` | telemetry + summary 除外の日別件数（v1 主指標） | `/api/heatmap` の `count` および `/api/heatmap/debug` の `shipped_density` |
| `telemetry_count` | `source="web-form-ui"` events の日別件数 | `/api/heatmap/debug` の `telemetry_count` |
| `life_count` | `raw_count - telemetry_count` | `/api/heatmap/debug` の `life_count`（現状は `shipped_density` と同値） |

### 関係式

```
raw_count[date] = shipped_density[date] + telemetry_count[date]
```

### v1 debug 導線

`/api/heatmap/debug` は検証専用エンドポイントであり、実運用 UI では使用しない。

1. `GET /api/heatmap` は `shipped_density` を返す（telemetry 除外）。
2. `GET /api/heatmap/debug` は `raw_count` / `shipped_density` / `telemetry_count` / `life_count` を返す。
3. `raw_count - shipped_density = telemetry_count`。この差分が大きい場合、telemetry が density を過大にしていたことを意味する。
4. `life_count` は現状 `shipped_density` と同値であり、debug 用の概念ラベルとして扱う。

### 代表日の照合手順

```bash
curl http://localhost:8080/api/heatmap/debug | python3 -m json.tool
curl http://localhost:8080/api/heatmap | python3 -m json.tool
curl http://localhost:8080/api/heatmap/debug | python3 -c "
import json, sys
for d in json.load(sys.stdin):
    if d['telemetry_count'] > 0:
        print(d['date'], 'raw:', d['raw_count'], 'shipped:', d['shipped_density'], 'telem:', d['telemetry_count'])
"
```

期待される観察結果:

- `raw_count >= shipped_density`
- `raw_count - shipped_density == telemetry_count`
- `life_count == shipped_density`

### Shipped UI tooltip の意味

現在の tooltip: `item.date + ': ' + item.count + '件'`（`src/personal_mcp/adapters/http_server.py:670`）

- 現在の `count` = `shipped_density`（user-authored events のみ）

tooltip の `件` という単位はそのまま維持してよい。意味は「その日に記録した活動の件数」に対応する。tooltip ラベルの変更判断は #257 のスコープ。

---

## 7. #256 / #257 への dependency と terminology

### #256 が参照すべき箇所

- **Section 2**: observation layer（除外条件 `source != "web-form-ui"`）
- **Section 3**: `shipped_density` の定義式
- **Section 4**: telemetry weight 0 の採用根拠と low weight / separate axis の非採用理由
- **Section 6**: `raw_count` / `shipped_density` / `telemetry_count` の定義と関係式

### #257 が参照すべき箇所

- **Section 2**: observation layer（shipped UI が数える対象）
- **Section 3**: `shipped_density` の定義式
- **Section 4**: telemetry を shipped UI の density から除外する根拠
- **Section 5**: `life_density` / `system_density` concept（内部 terminology）

### terminology table（#256 / #257 共通 internal terminology）

| term | 定義 | public interface 化 |
|---|---|---|
| `raw_count` | summary 除外のみの日別件数（現在挙動） | なし（内部のみ） |
| `shipped_density` | telemetry + summary 除外の日別件数（v1 目標） | なし（内部のみ） |
| `telemetry_count` | `source="web-form-ui"` events の日別件数 | なし（内部のみ） |
| `life_density` | `shipped_density` の concept 語 | 保留（Section 5） |
| `system_density` | summary + telemetry events の日別件数 | 保留（Section 5） |
| observation layer | shipped UI の集計対象 events の集合 | 仕様概念（interface 化なし） |

---

## 8. スコープ外・提案止まり・後続課題

### この文書のスコープ外（提案止まり / 人間レビュー必須）

- `/api/heatmap` の response shape 変更（`{date, count}` → 別形式）
- `life_density` / `system_density` の公開 interface 化
- color scale の最終設計（thresholds の意味的根拠付け）
- telemetry taxonomy 全体の再設計（新 event_name / ui_mode の追加）
- UI 操作方式の最終決定

### 人間レビュー必須の未確定事項

- `source != "web-form-ui"` フィルタが将来の telemetry 種別追加時に成立するか（新 `source` 値が増えた場合の拡張方針）
- `life_count` を将来も `shipped_density` の別名として維持するか、より広い concept に拡張するか

### 後続 Issue dependency

| Issue | 参照 Section | 内容 |
|---|---|---|
| #256 | 2, 3, 4, 6 | debug surface 実装（`raw_count` / `shipped_density` / `telemetry_count` を見比べられる導線） |
| #257 | 2, 3, 4, 5 | color scale 検討（shipped UI がどの density を色付け対象にするかの前提固定） |

---

## 関連ドキュメント

- `docs/design-principles.md` — 設計原則（原則 2: Human Observability 基盤）
- `docs/event-contract-v1.md` — Event Contract v1（`source` / `domain` フィールド定義）
- `docs/mvp-contract-decisions.md` — MVP 向け実装方針（summary 保存戦略）
- `docs/kind-taxonomy-v1.md` — kind taxonomy（telemetry は `kind: "interaction"`）
- `src/personal_mcp/tools/daily_summary.py` — `count_events_by_date` 実装
- `src/personal_mcp/tools/log_form.py` — `ui_event_add_sqlite`（telemetry 書き込み）
- `src/personal_mcp/adapters/http_server.py` — `/api/heatmap` handler と `heatColor`

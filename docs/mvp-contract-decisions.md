# MVP Contract Decisions — Annotation / Interpretation / Summary 責務境界

> この文書は Issue #148 で確定した MVP 向けの実装方針を記録する。
> 設計思想の背景は [`docs/design-principles.md`](./design-principles.md) を参照。
> Event Contract v1 の schema 定義は [`docs/event-contract-v1.md`](./event-contract-v1.md) を参照。
>
> **この文書は決定事項の記録であり、実装仕様書ではない。**
> 実装 Issue はこの文書をリンクして参照する。

---

## A. Annotation 保存位置

**決定: 分離（別レコード）方式を採用する**

Annotation は既存 event record を変更せず、新規 event record として JSONL に append する。

ルール:

- Annotation record は既存 Event Contract v1 形式に従う（`v=1`, `ts`, `domain`, `kind`, `data`）
- `kind` は `"note"` を使用する（Annotation に固有の kind は MVP では導入しない）
- 元 event を参照する場合は `ref` フィールドに元 event の識別子を記載する
- 後付け annotation は既存 event を書き換えない。必ず新規レコードとして append する

注記:

- event 書き込み時点で `data` 内に補助情報を含めることは Event 層の表現拡張として扱う
- それは Annotation としては扱わない。Annotation は常に別 record（`kind: "note"`）+ `ref` で表現する

理由:

- append-only 原則: 既存 event を変更できないため、後付け annotation は必然的に別レコードとなる
- Event Contract v1 の `ref` フィールドで参照関係を表現できる
- 専用の annotation ストレージや join ロジックを不要とし、実装を最小にする

---

## B. Interpretation の位置づけ

**決定: Interpretation は summary 生成時の処理として位置づける（summary 層の責務）**

ルール:

- Event 層・Annotation 層には interpretation（解釈・評価・パターン認識）を含めない
- Interpretation は「日次 summary の生成」フェーズで実施する
- Interpretation の結果は summary event として記録する
- MVP では Interpretation の実装は summary 生成の一部として扱い、独立した実装層は設けない

この決定により、`docs/design-principles.md` の 3 層構造における Interpretation 層は、
MVP 期間中は summary 生成処理の内部フェーズとして実現する。

---

## C. 日次 Summary の保存戦略

**決定: 派生保存を採用する**

ルール:

- 日次 summary は計算後に JSONL に append して保存する（都度再生成しない）
- Summary record は Event Contract v1 形式に従う
  - `domain`: `"summary"` を使用する
  - `kind`: `"artifact"` を使用する
  - `data.date`: 対象日付（`YYYY-MM-DD` 形式）
  - `data.text`: summary テキスト
  - `source`: `"generated"` を使用する
- Summary は派生データであり、ソースイベントから再生成可能であるという属性を持つ
  - ただし MVP では再生成ロジックの実装は含まない
- 同一日の summary が複数 append されている場合、reader は最新レコードを有効とする

理由:

- 毎回再生成は LLM 呼び出し等の重い処理を要するため、MVP では保存を優先する
- append-only 原則に準拠する（summary を上書きではなく追記する）
- 同日の再生成は新規 append で表現し、最新が有効という単純ルールで解決する

### Summary record の例

```json
{
  "v": 1,
  "ts": "2026-03-07T23:59:00+09:00",
  "domain": "summary",
  "kind": "artifact",
  "data": {
    "date": "2026-03-07",
    "text": "eng: Event Contract 整理を進めた。poe2: T16 map を周回した。"
  },
  "source": "generated"
}
```

---

## D. GitHub 同期 Event の source / ref ルール

GitHub から取得・同期したイベントには以下のルールを適用する。

### source ルール

| 生成元 | `source` 値 |
|---|---|
| 手動入力 | `"manual"` |
| GitHub 自動同期 | `"github"` |
| GitHub 一括 import | `"github-import"` |

### ref ルール

| 対象 | `ref` 形式 | 例 |
|---|---|---|
| GitHub Issue | `"#<number>"` | `"#148"` |
| GitHub PR | `"PR#<number>"` | `"PR#42"` |
| GitHub commit | short SHA（7 文字以上） | `"abc1234"` |
| 複数参照 | スペース区切り（先頭を主参照） | `"#148 #149"` |

補足ルール:

- `source: "github"` または `"github-import"` を付与する場合、可能な限り `ref` も付与する
- `ref` の形式は Event Contract v1 の `ref` フィールド（optional string）の範囲内で運用する
- GitHub 同期 event の `domain` は同期元の activity 種別に応じて設定する（`"eng"`, `"work"` 等）
- `source: "github"` を付与したイベントに手動で `annotation` を追加する場合は Section A のルールを適用する

### GitHub 同期 event の例

```json
{
  "v": 1,
  "ts": "2026-03-07T10:00:00+09:00",
  "domain": "eng",
  "kind": "milestone",
  "data": {
    "text": "Issue #148 をクローズした"
  },
  "source": "github",
  "ref": "#148",
  "tags": ["docs", "contract"]
}
```

---

## スコープ外（この文書では決めないこと）

- schema migration の実装
- Event Contract v2 の新設
- 既存データの移行実装
- UI 実装 / GitHub 同期実装 / summary 生成ロジックの実装
- Annotation / Interpretation の独立した実装層の設計

---

## 後続 Issue 参照ガイド

この文書の各 Section は独立してリンク可能である。

| 後続作業 | 参照 Section |
|---|---|
| Annotation 実装 | [Section A](#a-annotation-保存位置) |
| Summary 生成実装 | [Section B](#b-interpretation-の位置づけ), [Section C](#c-日次-summary-の保存戦略) |
| GitHub 同期実装 | [Section D](#d-github-同期-event-の-source--ref-ルール) |

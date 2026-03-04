# Event Contract v1

> Warning
> この文書は目標契約（v1）を定義する。現行ログは未準拠（legacy record）であり、移行は別 issue で扱う。

Issue #79 の Event Contract v1 を、現行の JSONL 保存形式との差分を明示した上で固定する文書。

## A. Contract v1

### Required top-level keys

| key | type | meaning |
|---|---|---|
| `v` | integer | record-level schema version。`1` を必須とする |
| `ts` | string | RFC 3339 / ISO 8601 の timezone offset 付き timestamp |
| `domain` | string | activity domain |
| `kind` | string | event kind |
| `data` | object | domain 固有の可変 payload |

### Optional top-level keys

| key | type | meaning |
|---|---|---|
| `tags` | array of string | filter / grouping 用の補助情報。省略可能 |
| `source` | string | writer / watcher / import などの生成元 |
| `ref` | string | issue 番号や外部 ID などの参照 |

### Rules

- `ts` は timezone 付きでなければならない。UTC 保存を推奨する。
- `data` の内部構造は v1 では固定しすぎない。domain ごとに拡張してよい。
- `tags` は optional とする。理由は、最低契約を reader-first で保ちつつ、自動記録や import 系イベントで空配列の常時付与を強制しないため。
- `text` は v1 の required key には含めない。generic reader の本文表示は `data.text` を best-effort で使ってよいが、存在しない場合は `domain` / `kind` / `ref` などから要約表示してよい。
- unknown top-level key と unknown `data` key は、v1 reader が無視して読み進めてよい。

### Representative v1 examples

#### poe2 / session

```json
{
  "v": 1,
  "ts": "2026-03-04T20:10:00+09:00",
  "domain": "poe2",
  "kind": "session",
  "data": {
    "text": "T16 map を 40 分周回して breach の感触を確認した",
    "duration_min": 40,
    "target": "breach farming"
  },
  "tags": ["mapping", "breach"],
  "source": "manual"
}
```

#### general / note

```json
{
  "v": 1,
  "ts": "2026-03-04T18:00:00+09:00",
  "domain": "general",
  "kind": "note",
  "data": {
    "text": "JSONL の最低契約を先に固定したい"
  },
  "source": "manual"
}
```

#### eng / artifact

```json
{
  "v": 1,
  "ts": "2026-03-04T22:15:00+09:00",
  "domain": "eng",
  "kind": "artifact",
  "data": {
    "text": "Event Contract v1 の設計メモを更新した",
    "artifact_type": "design_doc",
    "status": "updated"
  },
  "tags": ["docs"],
  "ref": "#80",
  "source": "manual"
}
```

## B. Legacy record

現行実装が `events.jsonl` に保存している record は、v1 ではなく legacy record である。

典型形:

```json
{
  "ts": "2026-03-04T11:00:00+00:00",
  "domain": "eng",
  "payload": {
    "text": "JSONL append-only方針を確認",
    "meta": {
      "kind": "milestone",
      "source": "manual",
      "ref": "#79"
    }
  },
  "tags": ["schema"]
}
```

legacy record の特徴:

- `v` が存在しない
- domain 固有データは `data` ではなく `payload`
- `kind` / `source` / `ref` はトップレベルではなく `payload.meta.*`
- `payload.meta` 自体が省略される場合がある
- 現行 reader / CLI の一部は `payload.text` を本文として扱う

`v` が無い以上、legacy record は Event Contract v1 準拠ではない。

## C. Mapping

| legacy record | v1 contract | rule |
|---|---|---|
| `ts` | `ts` | そのまま対応 |
| `domain` | `domain` | そのまま対応 |
| `payload` | `data` | キー名を変更して対応 |
| `payload.text` | `data.text` | `text` を使う reader は best-effort で参照先を移す |
| `payload.meta.kind` | `kind` | `meta.kind` がある場合にトップレベルへ昇格 |
| `payload.meta.source` | `source` | `meta.source` がある場合にトップレベルへ昇格 |
| `payload.meta.ref` | `ref` | `meta.ref` がある場合にトップレベルへ昇格 |
| `tags` | `tags` | 値はそのまま。v1 では省略も許容 |
| `v` なし | `v: 1` | 既存 record に対して暗黙補完しない。legacy は legacy として扱う |

補足:

- `v` の追加は field としては単純だが、「既存 record を v1 とみなす」ことはしない。
- `payload.meta.kind` が無い legacy record は、対応する `kind` を一意に決められない場合がある。
- `payload` 全体を `data` に写す場合でも、`meta` を残すかどうかは移行 issue 側で決める。この Issue では決めない。

## D. Tolerance

当面の reader / validator 方針は、writer strict / reader tolerant を維持しつつ、v1 と legacy の両読みに寄せる。

- v1 writer は `v`, `ts`, `domain`, `kind`, `data` を必須として書く
- 当面の reader は次のどちらも受理してよい
  - v1 record: `v=1` と required keys を持つ record
  - legacy record: `payload` 形状で `v` を持たない record
- validator を導入する場合も、少なくとも移行完了までは `strict-v1` と `tolerant-read` を分けてよい
- unknown top-level key と unknown `data` key は無視してよい
- legacy を読んだときに `kind` / `source` / `ref` が欠けていても、reader は失敗より継続を優先してよい

この tolerance は恒久互換レイヤの要求ではなく、移行完了までの運用方針である。

## E. Non-goals

この Issue / PR では次をやらない。

- 実装コードの変更
- 既存 JSONL の migration
- reader / validator の実装追加
- `data` 内部 schema の標準化
- domain allowlist や taxonomy の最終確定
- legacy record を自動で v1 扱いする互換レイヤの導入

将来の別 issue 候補:

- legacy -> v1 migration 方針の定義
- reader tolerance の実装とテスト
- strict validator の導入可否の整理

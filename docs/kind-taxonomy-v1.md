# Kind Taxonomy v1

> **Note (Legacy vs v1)**
> This document defines the **kind taxonomy for Event Contract v1**.
> **Current implementation and README are still based on the legacy record format** (e.g. `payload` / `payload.meta.kind`) and are **not yet v1-compliant**.
> Therefore, this taxonomy is a **forward-looking spec** for v1, not a description of what is stored today.
> For the v1 contract and terminology, see `docs/event-contract-v1.md`.

## Overview

Event Contract v1 では、すべてのイベントが 2 つの軸で識別される。

| field | role | examples |
|---|---|---|
| `domain` | どの活動文脈で起きたか | `poe2`, `eng`, `work`, `general` |
| `kind` | 何が起きたかという抽象的な型 | `note`, `session`, `artifact` |

`kind` は cross-domain な軸であり、どの domain でも再利用できるように設計する。
reader は `kind` を見て、domain をまたいだ大まかな解釈や集計を行える。

## Responsibility Split: kind vs domain

**`kind` の責務**

- イベントが「何であるか」の抽象的な型を表す
- 特定の domain に依存しない
- reader が `kind` を見て意味を読み取りやすい粒度を保つ

**`domain` の責務**

- どの活動・生活領域でそのイベントが起きたかを識別する
- domain 固有の `data` 構造を持つことを許容する

**原則**

- domain 固有の語を `kind` として導入しない
- ある `kind` が「この domain 以外では使わない」ものであってはならない
- kind の候補が浮かんだときは、「複数の domain で自然に使えるか」を確認する

## v1 Minimal Kind Set

以下の 6 種を v1 の minimal set として固定する。
この集合は意図的に最小限であり、拡張は Kind Add Rules に従う。

推奨フィールドは taxonomy guide であり、Event Contract v1 の required keys ではない。
各 `kind` の `data` は domain ごとに自由に拡張してよい。

### `note`

定義: 気づき、観察、短い記録、判断材料などの単発メモ。

境界メモ:
- 区切りや状態変化を宣言するなら `milestone`
- 成果物の作成・更新が主眼なら `artifact`

推奨フィールド（`data` 内）:
- `topic`

補助トップレベルキーとして使いやすいもの:
- `source`
- `ref`

### `session`

定義: 一定時間まとまって行った作業・活動・試行の記録。

境界メモ:
- 何かを整備した事実だけを残すなら `maintenance`
- 結果だけを記録するなら `milestone`

推奨フィールド（`data` 内）:
- `duration_min`
- `target`

補助トップレベルキーとして使いやすいもの:
- `ref`

### `artifact`

定義: 文書、画像、設定、成果物、アウトプットを作成または更新した記録。

境界メモ:
- 単なるメモや草案の断片なら `note`
- 完成・確定・公開などの節目を強調するなら `milestone`

推奨フィールド（`data` 内）:
- `artifact_type`
- `status`

補助トップレベルキーとして使いやすいもの:
- `ref`

### `milestone`

定義: 到達点、意思決定、完了、状態変化などの区切りを示す記録。

境界メモ:
- 途中経過の所感なら `note`
- 実施中の活動ログなら `session`
- 成果物の更新そのものなら `artifact`

推奨フィールド（`data` 内）:
- `result`
- `status`

補助トップレベルキーとして使いやすいもの:
- `ref`

### `interaction`

定義: 人、チーム、コミュニティ、外部システムとのやりとりや応答の記録。

境界メモ:
- やりとり自体ではなく、その後の作業を残したいなら `session`
- 受け取った内容のメモだけなら `note`

推奨フィールド（`data` 内）:
- `with`
- `channel`

補助トップレベルキーとして使いやすいもの:
- `ref`

### `maintenance`

定義: 整理、保守、更新、棚卸し、環境整備など、運用を安定させるための手入れの記録。

境界メモ:
- 時間を区切った作業全体を記録したいなら `session`
- 成果物の更新が主目的なら `artifact`

推奨フィールド（`data` 内）:
- `target`
- `action`

補助トップレベルキーとして使いやすいもの:
- `ref`

## Mapping Guidance

- まず「このイベントで一番残したいものは何か」を決め、その主語に最も近い `kind` を選ぶ
- 短い気づきや観察なら `note`、時間幅のある実施ログなら `session` を基本にする
- 何かを作った・更新した事実が中心なら `artifact`、区切りや確定事項なら `milestone` を選ぶ
- 誰か・何かとのやりとり自体が主題なら `interaction` を選ぶ
- 整備・更新・片付け・保守で、運用安定化が主題なら `maintenance` を選ぶ
- 迷うケースでは「メモを残したい」のか「節目を宣言したい」のかで `note` と `milestone` を分ける
- 詳細な文脈は `kind` に押し込まず、`tags` / `ref` / `source` や `data` 内の補助キーで補う
- 迷ったら新しい `kind` を作らず、既存 `kind` のうち最も再利用しやすいものへ寄せる

> legacy record の `payload` / `payload.meta.kind` から v1 へのフィールドマッピングは `docs/event-contract-v1.md` の Mapping を参照。
> `payload.meta.kind` が存在しない legacy record は、対応する `kind` を一意に決められない場合がある。

## Kind Add Rules

- 追加理由が「新しい domain が増えたから」だけでは不十分であること
- 既存 `kind` のいずれにも自然にマッピングできず、継続的に分類の迷いが発生すること
- 単発の特殊ケースではなく、複数回・複数 domain で繰り返し出現する型であること
- 対象領域ではなく、イベントの型として定義できること
- `tags` / `ref` / `source` や `data` 内の補助フィールドでは吸収しきれないこと
- 追加提案には少なくとも以下を含めること
- 定義
- 既存 `kind` と分ける理由
- 該当例
- 非該当例
- 想定される複数 domain の利用例
- v1 の安定性を優先し、`kind` の追加頻度は低く保つこと

## Out of Scope

- domain allowlist の追加や見直し
- kind ごとの厳密な enum 実装や CLI バリデーション仕様
- Event Contract v1 以外のスキーマ変更
- `tags` taxonomy の定義
- 過去イベントの一括再分類
- domain 固有の派生 `kind` 設計
- v2 以降を見越した先行的な細分類

## Sample Events

以下は Event Contract v1 の完全なイベント例である。

### `note`

```json
{
  "ts": "2026-03-04T18:00:00+09:00",
  "domain": "general",
  "kind": "note",
  "data": {
    "text": "kind は cross-domain であるべきだという考えが固まった",
    "topic": "event taxonomy design"
  },
  "v": 1,
  "tags": ["design", "schema"],
  "source": "manual"
}
```

### `session`

```json
{
  "ts": "2026-03-04T20:10:00+09:00",
  "domain": "eng",
  "kind": "session",
  "data": {
    "text": "kind taxonomy v1 の設計方針を検討した",
    "duration_min": 60,
    "target": "kind taxonomy draft"
  },
  "v": 1,
  "tags": ["design", "docs"],
  "source": "manual",
  "ref": "#80"
}
```

### `artifact`

```json
{
  "ts": "2026-03-04T22:15:00+09:00",
  "domain": "eng",
  "kind": "artifact",
  "data": {
    "text": "kind taxonomy v1 の設計メモを更新した",
    "artifact_type": "design_doc",
    "status": "updated"
  },
  "v": 1,
  "tags": ["docs"],
  "ref": "#80",
  "source": "manual"
}
```

### `milestone`

```json
{
  "ts": "2026-03-04T23:45:00+09:00",
  "domain": "poe2",
  "kind": "milestone",
  "data": {
    "text": "Act 3 ボスを初クリアした",
    "result": "Act 3 first clear",
    "status": "reached"
  },
  "v": 1,
  "tags": ["act3", "boss"],
  "source": "manual"
}
```

### `interaction`

```json
{
  "ts": "2026-03-04T15:00:00+09:00",
  "domain": "work",
  "kind": "interaction",
  "data": {
    "text": "設計レビューを受けた",
    "with": "team-lead",
    "channel": "review"
  },
  "v": 1,
  "tags": ["design"],
  "source": "manual"
}
```

### `maintenance`

```json
{
  "ts": "2026-03-04T14:00:00+09:00",
  "domain": "eng",
  "kind": "maintenance",
  "data": {
    "text": "pre-commit hooks を最新バージョンに更新した",
    "target": "pre-commit",
    "action": "update"
  },
  "v": 1,
  "tags": ["tooling"],
  "source": "manual",
  "ref": "#67"
}
```

## Acceptance Criteria

- `kind` と `domain` の責務分離が本文中で明示されている
- `kind taxonomy v1` の目的が cross-domain 再利用と手動記録時の一貫性にあると明記されている
- Event Contract v1 と用語が揃い、`ts` / `domain` / `kind` / `data` / `v` を使う前提が明記されている
- `tags` / `source` / `ref` が Event Contract v1 の任意トップレベルキーとして扱われている
- v1 の最小 kind セットが 6 個に固定され、それぞれに定義・境界メモ・推奨フィールドがある
- 推奨フィールドは `data` 内のガイドとして記述され、Event Contract の必須要件としては扱われていない
- Mapping Guidance により、迷ったときの選び方が短い簡易ルールとして提示されている
- kind 追加ルールが、再利用性・安定性・既存 kind との差分を基準に定義されている
- 「新しい domain が増えたから」という理由だけでは kind を追加しない方針が本文で確認できる
- `tags` taxonomy 設計自体は本 Issue の範囲外であることが明記されている
- Event Contract v1 の完全なイベント例が少なくとも 3 つ含まれている
- domain 固有語を kind として増やさない方針が本文で確認できる

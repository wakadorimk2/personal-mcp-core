# candidate API v1

Issue #186 の最小実装に対応する `GET /api/candidates` 契約。
daily input UX MVP 方針（`docs/daily-input-ux-mvp.md`）の候補生成ルールを HTTP API として固定する。

## Endpoint

- `GET /api/candidates`

## Response

200 で候補配列を返す。最大 8 件。

```json
[
  { "text": "休憩", "source": "recent" },
  { "text": "作業開始", "source": "fixed" }
]
```

### Fields

- `text`: UI に表示する候補テキスト
- `source`: 候補ソース（`recent` / `today_frequent` / `7d_frequent` / `fixed`）

## Candidate rules

- cold start 判定は API 側で実施する
  - 対象イベント件数 `< 7`: `fixed` のみ返す
  - 対象イベント件数 `>= 7`: 4ソースを有効化
- マージ優先順: `recent > today_frequent > 7d_frequent > fixed`
- 正規化後テキスト重複は 1 件に統合し、より高優先度ソースを採用する
  - 正規化は `strip + lower`（前後空白除去 + 小文字化）
- 最終表示件数は常に最大 8 件

## Source extraction

- `recent`: 直近 10 件のイベント `data.text`（新しい順）
- `today_frequent`: 当日イベント `data.text` の頻度順
- `7d_frequent`: 過去 7 日（当日含む）のイベント `data.text` の頻度順
- `fixed`: API 内定義の固定候補

## Notes

- 候補対象は `domain != summary` かつ `kind != interaction` のイベントに限定する。
- 本仕様は MVP 期間の v1 とし、閾値や固定候補語彙は follow-up Issue で調整する。

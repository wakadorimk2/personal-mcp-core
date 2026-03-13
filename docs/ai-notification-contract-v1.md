# AI Notification Contract v1

Issue #224 で扱う、AI エージェント向け通知の最小契約を定義する。
目的は、Codex CLI / Claude Code / local scripts / make / CI などが notifier に渡す
イベント種別とメッセージ形式の意味揺れを減らすことにある。

この文書は「notify wrapper に渡す共通入力」の v1 を定義する。
通知チャネル実装、永続化、分析用途のデータ設計は対象外とする。

## Goal

- 通知イベント種別を最小集合で固定する
- AI エージェント識別子の持ち方を整理する
- notifier に渡すメッセージフォーマットを定義する

## Non-goal

- Windows 通知や Discord Webhook の具体実装
- Codex CLI / Claude Code 側の実装詳細
- 通知履歴保存やダッシュボード向け schema 設計
- すべての AI ツールへ最初から共通化できる完全仕様の確定

## 1. Event Types

v1 では次の 4 種を固定する。

| `event_type` | 送信タイミング | 人間に伝えたい意味 | 備考 |
|---|---|---|---|
| `task_completed` | 依頼された作業単位が正常終了したとき | 確認または次アクションに進める | 部分進捗では使わない |
| `needs_input` | エージェントが人間の入力・承認・判断待ちになったとき | 返答しないと進まない | 追加質問、権限承認、判断待ちを含む |
| `task_failed` | エージェント実行が失敗で止まり、介入が必要なとき | エラー対応または再実行が必要 | 単なる入力待ちは含めない |
| `long_task_finished` | 長時間の watch / build / sync / batch などが終わったとき | バックグラウンド監視を外してよい | 作業全体の完了とは限らない |

### Mapping Rules

- 完了したのが「依頼された task」なら `task_completed` を使う
- 完了したのが「長時間ジョブ」だけなら `long_task_finished` を使う
- 止まった理由が人間の返答不足なら `needs_input` を使う
- 止まった理由がエラーや失敗なら `task_failed` を使う
- v1 では event name を細分化しない。追加が必要なら follow-up Issue で検討する

## 2. Agent Identity

例として挙がっている `builder / advisor / ops / claude` は単一軸ではない。
`builder / advisor / ops` は役割、`claude` は実行系に近く、1 つの `agent_id` 文字列へ混在させると意味がぶれる。

そのため v1 では、通知元の識別を次の 2 軸で持つ。

| field | required | meaning | examples |
|---|---|---|---|
| `agent.runtime` | yes | 実際に通知を発火した実行系 | `codex`, `claude_code`, `local_script`, `make`, `ci` |
| `agent.role` | recommended | 作業レーン / 責務上の役割 | `builder`, `advisor`, `ops`, `human` |
| `agent.instance` | no | 並列実行の識別子 | `builder-1`, `wsl-main`, `runner-a` |
| `agent.label` | no | 表示用の任意ラベル | `builder (Codex)` |

### Rules

- 安定識別は `runtime` を基準にする
- `role` が分かる環境では `role` も付ける
- `label` は表示専用であり、分岐条件に使わない
- 単一文字列 ID が必要な実装では `role@runtime` を推奨する
  - 例: `builder@codex`
  - `role` が無い場合は `runtime` のみでよい

## 3. Notification Message Format

notify wrapper に渡す共通入力は次の JSON object とする。

### Required fields

| field | type | meaning |
|---|---|---|
| `v` | integer | schema version。v1 では `1` 固定 |
| `event_type` | string | Section 1 の enum |
| `occurred_at` | string | RFC 3339 timestamp |
| `agent` | object | Section 2 の agent 情報 |
| `title` | string | 1 行で意味が通る通知見出し |

### Optional fields

| field | type | meaning |
|---|---|---|
| `body` | string | 補足説明。1-3 行程度の plain text を想定 |
| `task_ref` | string | issue / PR / job 名などの参照 |
| `run_url` | string | 直接確認できる URL |
| `next_action` | string | 人間に求める次の行動 |
| `metadata` | object | channel 非依存の補助情報 |

### Rendering Rules

- `title` は単体で見ても意味が通ること
- `body` は省略可。長いログ全文は入れず、要点だけを書く
- `next_action` は `needs_input` では実質必須、`task_failed` では強く推奨
- `metadata` は補助用途に留め、notifier の分岐を `metadata` 依存にしない

## 4. Current Channel Projection and Discord Minimum Scope

Section 3 の JSON object は notify wrapper へ渡したい上位契約であり、
channel adapter が現時点で直接受け取れる field とは一致しない。

現状の `scripts/notify` が channel adapter に渡すのは次の正規化済み入力のみ:

- `NOTIFY_MESSAGE`
- `NOTIFY_TITLE`
- `NOTIFY_EVENT`
- `NOTIFY_SOURCE`
- `NOTIFY_SEVERITY`
- `NOTIFY_VERBOSITY`
- stdin に流す message body

このため Discord webhook の最小実装（#238）は、上記 projection だけで送れる範囲に留める。
optional metadata 候補の扱いは次の通り整理する。

| candidate | contract 上の位置づけ | Discord 最小実装で送るか | 判断 |
|---|---|---|---|
| `body` | optional。補足説明本文 | 送る | 既存の `NOTIFY_MESSAGE` に投影できる |
| `task_ref` | optional。issue / PR / job 参照 | 送らない | wrapper が field を adapter へ渡していない。必要なら wrapper 拡張で扱う |
| `run_url` | optional。確認用 URL | 送らない | wrapper が field を adapter へ渡していない。必要なら wrapper 拡張で扱う |
| `next_action` | optional。人間に求める次の行動 | 送らない | `needs_input` / `task_failed` では有用だが、現状は wrapper 拡張なしに adapter へ渡せない |
| `metadata` | optional。channel 非依存の補助情報 | 送らない | key の正規化と adapter への受け渡し方式を別途決める必要がある |

補足:

- `NOTIFY_SEVERITY` / `NOTIFY_VERBOSITY` は wrapper が kind / event から解決する
  advisory policy metadata であり、Section 3 の上位入力 JSON に必須追加するものではない
- 現時点では adapter が rendering や suppression に必ず使う前提は置かない

### Rules for #238

- Discord adapter は既存の wrapper projection だけを入力として使う
- `task_ref` / `run_url` / `next_action` / `metadata` のために ad-hoc な `NOTIFY_*` を増やさない
- optional metadata が必要になったら wrapper 契約の follow-up issue として切り出す

## 5. JSON Example

### `task_completed`

```json
{
  "v": 1,
  "event_type": "task_completed",
  "occurred_at": "2026-03-09T09:45:00+09:00",
  "agent": {
    "runtime": "codex",
    "role": "builder",
    "label": "builder (Codex)"
  },
  "title": "builder finished issue #224",
  "body": "AI notification contract v1 draft is ready for review.",
  "task_ref": "#224",
  "run_url": "https://github.com/wakadorimk2/personal-mcp-core/issues/224"
}
```

### `needs_input`

```json
{
  "v": 1,
  "event_type": "needs_input",
  "occurred_at": "2026-03-09T10:10:00+09:00",
  "agent": {
    "runtime": "claude_code",
    "role": "advisor",
    "instance": "advisor-1"
  },
  "title": "advisor needs maintainer decision",
  "body": "Two naming options remain for the notification wrapper output.",
  "task_ref": "#224",
  "next_action": "Choose the canonical output field name."
}
```

## 6. Event-Type Message Guidance

| `event_type` | `title` の期待 | `body` の期待 | `next_action` |
|---|---|---|---|
| `task_completed` | 完了対象が分かる | 完了内容または成果物の要約 | 任意 |
| `needs_input` | 何待ちか分かる | 足りない入力や判断対象 | 必須扱い |
| `task_failed` | 失敗対象が分かる | 原因の短い要約 | 強く推奨 |
| `long_task_finished` | 終了した長時間ジョブが分かる | 所要時間や結果の要約 | 任意 |

現在の `scripts/notify` 既定 policy では、`needs_input` と `task_failed` を
人間の介入が必要な通知として `warning/critical` または `error/critical` に寄せる。
`task_completed` と `long_task_finished` は `info/normal` が既定で、`smoke_test` は
kind policy により `task_completed` へ投影しつつ `info/debug` として扱う。

## 7. Out of Scope for v1

- channel ごとのタイトル文字数制限や装飾仕様
- retry policy、dedupe key、通知抑制ルール
- 通知イベントの保存 schema
- `task_paused` や `task_cancelled` など追加 enum
- runtime ごとの専用 field

## 8. Current Codex CLI bridge

この repo の現状実装では、Codex CLI の `notify` hook から渡される
`agent-turn-complete` payload を `scripts/codex_notify.py` で受け、
`scripts/notify` に次の形で投影する。

- `event_type`: `task_completed`
- `agent.runtime`: `codex`
- `agent.label/source`: top-level `client` があれば利用し、なければ `codex`
- `title`: `input-messages`（互換で `input_messages` も許容）の末尾
- `body`: `last-assistant-message`

これにより Codex 側の payload 形式を `scripts/notify` へ直接広げず、
wrapper entrypoint を 1 つに保つ。

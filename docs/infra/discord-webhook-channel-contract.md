# Discord webhook channel contract

Issue #237 で扱う、`scripts/notify` 向け Discord webhook adapter の最小契約を定義する。
目的は、実装前に設定方法、送信 payload、失敗時の扱いを固定し、channel adapter の
仕様ぶれを防ぐことにある。

この文書は `scripts/notify.d/discord` を追加するときの v1 契約であり、
Discord 送信実装そのものは対象外とする。

## Goal

- Discord webhook adapter の必須設定を固定する
- `notify` wrapper から渡される最小入力を Discord payload へどう写像するか定義する
- 設定不備と HTTP 失敗時の終了方針を固定する

## Non-goal

- Discord bot や双方向操作
- embed / attachment / rich metadata の最終仕様
- retry policy や queueing
- `notify` wrapper 自体の CLI 変更

## 1. Adapter location and invocation

- channel 名は `discord` とする
- adapter path は `scripts/notify.d/discord` とする
- 呼び出し元は既存 `scripts/notify` wrapper のみを想定する
- adapter は stdin と `NOTIFY_*` 環境変数の両方を読める前提でよい

## 2. Configuration

### Required

| env var | meaning |
|---|---|
| `DISCORD_WEBHOOK_AI_STATUS` | Discord incoming webhook URL |

### Optional

| env var | meaning |
|---|---|
| `DISCORD_WEBHOOK_USERNAME` | webhook 送信時の表示名 override |
| `DISCORD_WEBHOOK_AVATAR_URL` | webhook 送信時の avatar override |

### Rules

- `DISCORD_WEBHOOK_AI_STATUS` が未設定または空文字なら adapter は送信を試みない
- channel 選択は既存どおり `NOTIFY_CHANNEL=discord` または `notify --channel discord` を使う
- Discord 固有の設定は adapter 内に閉じ込め、`scripts/notify` の共通引数へ追加しない

## 3. Input contract from `scripts/notify`

Discord adapter は次の入力を受け取る。

| input | required | meaning |
|---|---|---|
| `NOTIFY_MESSAGE` | yes | 通知本文 |
| `NOTIFY_TITLE` | no | 1 行の見出し |
| `NOTIFY_EVENT` | yes | イベント種別 |
| `NOTIFY_SOURCE` | no | 通知元ラベル |
| stdin | yes | `NOTIFY_MESSAGE` と同じ本文 |

`NOTIFY_MESSAGE` が空になる入力は wrapper 側で弾かれるため、adapter は
wrapper からの正規化済み入力を前提にしてよい。

## 4. Minimal Discord payload

v1 の Discord webhook payload は `content` を使った plain text 送信のみとする。
embed、attachment、component は使わない。

送信 payload の最小構成は次の JSON object とする。

| field | required | source |
|---|---|---|
| `content` | yes | Section 5 の整形結果 |
| `username` | no | `DISCORD_WEBHOOK_USERNAME` |
| `avatar_url` | no | `DISCORD_WEBHOOK_AVATAR_URL` |

## 5. Rendering rules

`content` は次のルールで組み立てる。

1. `NOTIFY_TITLE` があれば 1 行目を `**<title>**` とする
2. 本文行に `NOTIFY_MESSAGE` をそのまま入れる
3. 末尾に provenance 行として ``[`<event>`]`` または ``[`<event>` from `<source>`]`` を付ける

例:

### title と source がある場合

```text
**issue #237 draft is ready**
Discord adapter contract v1 is ready for review.
[`task_completed` from `codex-tui`]
```

### title だけ無い場合

```text
Need maintainer decision for the Discord payload format.
[`needs_input` from `advisor`]
```

### source も無い場合

```text
Long-running sync finished.
[`long_task_finished`]
```

Rules:

- `NOTIFY_MESSAGE` を主本文とし、event/source は補助情報として末尾へ寄せる
- `NOTIFY_TITLE` は Discord 上で視認しやすいよう太字 1 行に限定する
- Markdown 装飾は title の強調以外を前提にしない
- v1 では AI notification contract の optional fields を Discord 専用 field へ展開しない

## 6. Failure and exit-code policy

### Missing webhook configuration

- `DISCORD_WEBHOOK_AI_STATUS` が未設定または空文字なら stderr に原因を書く
- exit code は `2` とする
- これは usage / configuration error として扱い、HTTP request は送らない

### HTTP or transport failure

- Discord webhook POST が non-2xx で終わった場合は stderr に status を書く
- DNS, timeout, TLS など送信失敗も stderr に短く書く
- exit code は `1` とする

### Success

- Discord が成功応答を返した場合は exit code `0` とする
- 標準出力に追加メッセージは出さない

## 7. Out of scope for v1

- mention 制御
- retry / backoff
- message splitting
- embeds への移行
- channel ごとの色や装飾ルール

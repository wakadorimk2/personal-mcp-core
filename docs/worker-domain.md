# worker domain contract

> 関連 Issue: #324
> 関連ポリシー: [`docs/domain-extension-policy.md`](./domain-extension-policy.md)
> 関連 coordination 境界: [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md)

## 目的

`worker` domain は、AI worker board 向けの状態イベントを append-only で記録するための
最小 domain である。

対象は「どの worker が」「どの terminal で」「どの issue / task を」
「どの状態で扱っているか」の観測に限定する。

## 境界

- 含むもの
  - worker 状態の更新
  - board 表示に必要な最新状態の復元
- 含まないもの
  - GitHub / Project board 連携
  - 通知契約
  - 人間向け評価やスコア
  - TUI / アニメーション表現
  - claim / handoff / maintainer override の authoritative record

## 既存 domain と重複しない理由

`eng` / `worklog` は人間の作業内容そのものを記録する domain だが、
`worker` は AI runtime / terminal ごとの状態観測を目的とする。

`general` でも単発メモは残せるが、
worker board では `worker_id` / `terminal_id` / `status` を持つ定型イベントが必要なため、
専用 domain とする。

## イベント例

```json
{
  "v": 1,
  "ts": "2026-03-11T08:55:00+09:00",
  "domain": "worker",
  "kind": "milestone",
  "data": {
    "text": "Claude-1 is working on #324",
    "worker_id": "claude-1",
    "worker_name": "Claude-1",
    "terminal_id": "tty-1",
    "current_issue": "#324",
    "status": "working"
  },
  "tags": ["working"],
  "source": "worker-cli"
}
```

## フィールド

必須 top-level keys は Event Contract v1 に従う。

- `v`
- `ts`
- `domain`
- `kind`
- `data`

`worker` domain では `data` 配下に少なくとも以下を持つ前提とする。

- `text`
- `worker_id`
- `worker_name`
- `terminal_id`
- `status`

`current_issue` は任意。
これは worker が現在扱っている issue のヒントであり、
issue ownership や claim の成立を表すものではない。

`last_update` のような mutable field は持たず、
最新時刻はイベントの `ts` から復元する。

## status 値

初期実装で許可する状態:

- `working`
- `waiting`
- `reviewing`
- `idle`
- `done`

## privacy / secret / sensitive 情報

`worker` domain には、Issue 番号、短い task ラベル、terminal 識別子が入りうる。
認証情報、トークン、ローカル絶対パス、private URL のような秘匿情報は含めない。

board 表示の目的は観測であり、評価や優先度づけには使わない。

## テスト観点

- allowlist に `worker` を追加したとき、`event-add --domain worker` が通ること
- `worker-status-set` が定型イベントを追記すること
- `ai-board` / `worker-board` が worker ごとの最新状態を表示すること
- 不正 status が reject されること

## 互換性メモ

- Event Contract v1 の required keys を維持する
- worker 固有情報は `data` 配下に閉じる
- 互換レイヤは追加しない
- future で GitHub 連携を追加しても、この domain 自体は観測イベントのまま保つ

## 依存関係

この domain は Issue #324 の初期スコープに対応する。
GitHub integration や richer UI は follow-up Issue として分離する。

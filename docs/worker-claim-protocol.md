# worker claim protocol v1

> 関連 Issue: #375
> 関連 Issue: #373, #374, #378
> 関連 docs: [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md), [`docs/worker-domain.md`](./worker-domain.md)

## 目的

AI worker が同じ Issue を取り合わないための最小 protocol を定義する。

v1 では、強い自動ロックや lease 制御ではなく、
人手運用で壊れにくく、監査しやすく、後で bot 化しやすい
append-only の coordination protocol を優先する。

## 結論

- GitHub Issue comment 群を claim protocol の canonical event log とする
- current owner / current claim state は comment から導出する
- label は optional な可視化補助、registry は runtime observability 補助に留める
- v1 では `refresh` と自動 `expire` を入れず、`claim` / `release` / `handoff` / `maintainer override` に絞る

この方針により、
「Issue comment が現在状態そのものを背負う」形を避けつつ、
履歴を保ったまま単純な状態遷移で運用できる。

## design goals

- comment を current state ではなく canonical event log として扱う
- current state は導出結果として定義する
- manual distributed lock のような lease / timeout 依存を避ける
- maintainer が人手で介入できる
- 監査性と将来の自動化余地を両立する

## non-goals

- GitHub App / bot による強制排他
- 自動 `expire`
- `refresh` / heartbeat / lease renewal
- scheduler による自動再割当
- label を current state の正本にすること
- registry を claim source に昇格させること

## canonical source と責務境界

claim protocol の canonical source は、
GitHub Issue 上の protocol comment 群とする。

境界:

- GitHub Issue comments: claim / release / handoff / override の canonical event log
- labels: optional な可視化補助。canonical state を上書きしない
- registry / `worker` domain: runtime observability truth。claim 正本にしない

この境界により、
claim state は GitHub 側で共有され、
worker board や dashboard はそれを mirror しても二重正本にしない。

## protocol event model

v1 で定義する protocol event は以下に限定する。

| event | actor | effect | ref requirement |
|---|---|---|---|
| `claim` | worker | `unclaimed` issue を claim する | なし |
| `release` | current owner | active claim を終了する | active claim を参照 |
| `handoff_offer` | current owner | handoff 提案を開始する | active claim を参照 |
| `handoff_accept` | handoff target | handoff を成立させる | 最新の open offer を参照 |
| `maintainer_override` | maintainer | active claim または pending handoff を clear する | 対象 event を参照 |

各 protocol comment は少なくとも次の意味論的フィールドを持つ。

- `protocol`: `worker-claim/v1`
- `event_type`
- `worker_id`
- `runtime`
- `issue_number`
- `reason`
- `ref`
  - `release` / `handoff_offer` / `handoff_accept` / `maintainer_override` では必須
- `target_worker_id`
  - `handoff_offer` では必須

補足:

- event ordering は GitHub comment の `created_at` を主、comment id を副として扱う
- comment body 内の timestamp は補助情報であり、canonical ordering には使わない
- exact serialization は実装で固定してよく、baseline では
  `src/personal_mcp/tools/worker_claim.py` の serializer / parser を正本とする
- 実装 surface は `python -m personal_mcp.server worker-claim-state` と
  `python -m personal_mcp.server worker-claim-post` を使う

例:

```text
<!-- og-worker-claim:v1 -->
protocol: worker-claim/v1
event_type: claim
worker_id: codex-1
runtime: codex
issue_number: 375
reason: draft protocol spec
```

## derived current state

current claim state は protocol comments を順に replay して導出する。

導出対象:

- `unclaimed`
- `claimed(owner=<worker_id>, claim_ref=<comment>)`
- `handoff_pending(from=<worker_id>, to=<worker_id>, offer_ref=<comment>)`

ルール:

- 初期 state は `unclaimed`
- `handoff_pending` 中も current owner は handoff 元 worker のままとする
- `maintainer_override` 後の current state は `unclaimed`
- invalid event も event log には残すが、derived state は更新しない

このモデルでは current state を単一 comment に保存しない。
現在の owner は event log から都度導出される。

## event validity rules

### `claim`

- current state が `unclaimed` の場合のみ active claim を開始する
- active claim がある状態で出た後続 `claim` は conflict evidence として残るが、current owner は変えない

### `release`

- current owner のみ有効
- active claim を終了し、state を `unclaimed` に戻す

### `handoff_offer`

- current owner のみ有効
- target worker を明示して `handoff_pending` を開始する
- offer 時点では ownership は移らない

### `handoff_accept`

- target worker のみ有効
- 最新の open な `handoff_offer` を参照している場合に限り成立する
- 成立時点で ownership は target worker に移る

### `maintainer_override`

- maintainer のみ有効
- active claim または open handoff を clear する
- v1 では owner の直接付け替えには使わない
- override 後に別 worker が必要なら、新しく `claim` を残す

## stale claim の扱い

v1 では自動 `expire` を入れない。
stale claim は「時間経過で自動失効する状態」ではなく、
maintainer が stale / abandoned / invalid と判断したため
`maintainer_override` 可能な状態として扱う。

maintainer が override を使ってよい例:

- worker が異常終了し、`release` を残せない
- active claim が放置されている
- competing claim が発生し、人手で解消が必要
- `handoff_offer` 後に受け手が不在で pending が解消されない

この方針により、
lease timeout や clock skew による事故を v1 から持ち込まない。

## handoff 成立条件

handoff は 2 段階にする。

1. current owner が `handoff_offer` を残す
2. target worker が `handoff_accept` を残す

成立条件:

- offer が active claim を参照している
- accept が最新の open offer を参照している
- accept の `worker_id` が offer の `target_worker_id` と一致している
- offer が `release` または `maintainer_override` で無効化されていない

offer だけでは ownership は移らない。
これにより、handoff の片側だけで owner が勝手に切り替わる事故を避ける。

## 下流 Issue との接続点

### PLAYBOOK（#373）

- 着手条件は derived claim state を参照する
- `unclaimed` のとき着手可能
- `handoff_accept` により受け取った worker は、その accept を根拠に続行できる
- 中断 / handoff / 再開時に残す protocol event は本 spec を参照する

### WORKER_POLICY（#374）

- dispatch 前の collision check は derived claim state を参照する
- preferred runtime / fallback / reviewer 分離は本 spec でなく policy 側が定義する
- canonical source の再定義は行わない

### baseline implementation（#378）

- GitHub Issue comment への protocol event 記録経路を実装する
- derived state の取得ロジックを実装する
- label / registry mirror は optional とし、canonical state を上書きしない
- baseline command:

```bash
python -m personal_mcp.server worker-claim-state \
  --owner wakadorimk2 \
  --repo orange-garden \
  --issue-number 378 \
  --json

python -m personal_mcp.server worker-claim-post \
  --owner wakadorimk2 \
  --repo orange-garden \
  --issue-number 378 \
  --event-type claim \
  --worker-id codex-1 \
  --runtime codex \
  --reason "start claim baseline" \
  --dry-run
```

- `worker-claim-post` は `release` / `handoff_offer` / `handoff_accept` /
  `maintainer_override` で `--ref` を省略した場合、
  直前の derived state から active ref を補完する
- `--dry-run` を外すと GitHub Issue comment へ protocol event を実際に投稿する

## follow-up

- label mirror を採用する場合は、derived state の projection であることを明記する
- `refresh` や自動 `expire` が必要になった場合は、v1 へ追加せず別 Issue で検討する

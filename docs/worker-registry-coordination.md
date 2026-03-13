# worker registry coordination boundary

> 関連 Issue: #376
> 関連 Issue: #324, #375, #373, #374, #378, #379
> 関連 docs: [`docs/worker-domain.md`](./worker-domain.md), [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md), [`docs/AI_WORKFLOW.md`](./AI_WORKFLOW.md)

## 目的

既存の `events.db` / `worker` domain / `worker-status-set` / dashboard を、
AI worker orchestration における **registry coordination layer** として
どう位置づけるかを定義する。

この文書は「どこが canonical source か」と
「registry が持ってよい責務 / 持たない責務」を固定する。

## 結論

- registry は **worker runtime の観測 + 軽量 coordination 補助** を担う
- registry は **global ownership の決定者** にはしない
- `worker` domain の `current_issue` は **現在扱っている issue のヒント** であり、claim そのものではない
- claim / handoff / maintainer override の正本は、worker 全員が共有できる GitHub 側 metadata に置く

この方針により、既存 worker board の観測用途を保ちながら、
claim protocol と handoff flow が後から追加されても
責務衝突を起こしにくくする。

## registry の役割

registry が担うもの:

- worker ごとの最新 runtime 状態の観測
- terminal ごとの liveness と `last_update` の復元
- dashboard / `ai-board` が読む軽量な最新状態ビュー
- GitHub 側 canonical state を補助的に表示するための projection 先

registry が担わないもの:

- issue ownership の裁定
- claim / release / handoff の authoritative record
- maintainer override の最終記録
- GitHub Project の status / priority の正本管理

言い換えると、registry は **coordination の補助面** には入るが、
**排他制御や ownership の最終判定** までは担わない。

## canonical source matrix

| state | canonical source | registry の扱い | 理由 |
|---|---|---|---|
| worker status | `events.db` の `worker` domain event | 正本として保持 | `worker_id` / `terminal_id` / `status` / `last_update` は runtime ローカルで最も自然に生成されるため |
| claim state | GitHub Issue 側の claim record（#375 で定義） | 任意の mirror / cache は可、ただし正本にしない | claim は複数 runtime と maintainer が共有して読む必要があり、GitHub 側の可視性が高い |
| handoff state | GitHub Issue 側の handoff record（#375 で定義） | worker status として周辺状態を映してよいが、正本にしない | handoff は worker 間の引き継ぎ判断そのものなので、共有可視性を優先する |
| project status / priority | GitHub Project metadata | 持たない | orchestration policy では参照対象だが、registry に複製すると責務が二重化する |

## component boundary

### `events.db`

- append-only の runtime registry storage
- `worker` domain の最新状態を復元する基盤
- claim / handoff の正本 storage には昇格させない

### `worker` domain

- worker 観測イベント専用 domain
- 記録対象は `worker_id` / `worker_name` / `terminal_id` / `status` / `current_issue` のような
  runtime 状態に限定する
- GitHub Issue の ownership や override 決定は直接表現しない

### `worker-status-set`

- registry へ worker 状態を append する writer
- 書いてよいのは worker の runtime 状態のみ
- claim の取得 / 解放 / handoff 完了をこの command 単体で成立させない
- baseline 実装では `--current-issue` を **registry hint** として扱い、
  ownership を表す入力にはしない

### dashboard / `ai-board`

- registry を読んで最新 worker 状態を表示する reader
- 将来 GitHub 側 claim 情報を併記してもよいが、
  ownership 判定ロジックは dashboard に持たせない
- registry と GitHub 側に不一致がある場合は、
  GitHub claim/handoff を優先し、dashboard 側は stale / unknown として扱う
- baseline 実装では board row に `current_issue_source=registry_hint` と
  `ownership_source=github_issue` を含め、表示上も ownership 境界を注記する

## GitHub metadata との責務分担

GitHub 側に置く情報:

- 誰が issue を claim したか
- claim が release / handoff / override されたか
- どの worker へ handoff したいか、handoff が成立したか
- maintainer が介入した判断ログ

registry 側に置く情報:

- どの worker / terminal が今どの状態か
- いつ最後に更新されたか
- 今どの issue を扱っているつもりかという runtime ヒント

境界ルール:

- GitHub 側 metadata が collaboration truth
- registry 側 metadata が runtime observability truth
- `current_issue=#376` の registry 記録だけでは、`#376` を claim したことにはならない

## playbook / policy / protocol との接続点

### PLAYBOOK（#373）

- 着手条件、再開条件、handoff 完了条件は GitHub 側 claim/handoff record を参照する
- registry は「その worker が最近生きているか」「reviewing / waiting か」を補助的に示す

### WORKER_POLICY（#374）

- dispatch policy は task-class と runtime 適性を定める
- 実際に誰が占有中かの確認は GitHub 側 claim state を見る
- registry の freshness は dispatch の参考情報には使えるが、裁定根拠にはしない

### Claim Protocol（#375）

- GitHub Issue comments を canonical event log とする claim protocol を定義する
- current owner / current claim state は event log から導出する
- v1 では `refresh` / 自動 `expire` を入れず、stale claim は maintainer override で扱う
- registry はその protocol を補助的に可視化してよいが、正本の置換をしない

## divergence rule

GitHub 側と registry 側で状態がずれた場合は、次の順で扱う。

1. claim / handoff / override は GitHub 側を正として読む
2. worker の liveness / last seen は registry 側を正として読む
3. dashboard 表示で両者を混同しない
4. 一方を見て他方を上書きする自動同期は baseline では行わない

このルールにより、二重書きの見かけ上の不整合が起きても
「どちらを信じるべきか」が固定される。

## baseline implementation mapping

現行 baseline では、責務分担を次の経路に反映する。

- `worker-status-set`: `worker` domain event を append するだけで、
  claim / release / handoff は成立させない
- `ai-board` / `worker-board --json`: `current_issue` を返すが、
  併せて `current_issue_source=registry_hint` と
  `ownership_source=github_issue` を返す
- `ai-board` の標準出力: issue 列が hint であり、
  claim/handoff ownership は GitHub 側にあることを注記する

手動検証の最小手順:

```bash
python -m personal_mcp.server worker-status-set \
  --worker-id claude-1 \
  --terminal-id tty-1 \
  --current-issue 379 \
  --status working \
  --data-dir /tmp/og-registry-check

python -m personal_mcp.server ai-board --json --data-dir /tmp/og-registry-check
python -m personal_mcp.server ai-board --data-dir /tmp/og-registry-check
```

期待結果:

- JSON 出力に `current_issue`, `current_issue_source`, `ownership_source` が含まれる
- `current_issue_source` は `registry_hint`
- `ownership_source` は `github_issue`
- テキスト出力に「issue は registry hint」「ownership は GitHub」という注記が出る

## follow-up items

- #373: playbook 上の着手 / 中断 / handoff / 再開条件を、この境界に合わせて記述する
- #374: dispatch policy 上の確認順序を `GitHub claim -> registry observability` に揃える
- #379: dashboard や `worker-status-set` の baseline 実装を、この責務分担に沿って更新する
- #378: claim baseline 実装では GitHub 側 canonical path を使い、registry mirror は必要最小限に留める

## 非スコープ

- GitHub と registry の完全双方向同期
- `worker` domain schema の直ちの拡張
- scheduler や自動 claim 再割当
- dashboard UI の大規模改修

## リスク

- GitHub 側 write path が増えると manual operation が少し重くなる
- registry を正本にしないため、dashboard 単体では ownership 完了判定ができない

ただし、初期段階では「見えること」より「二重正本にしないこと」を優先する。

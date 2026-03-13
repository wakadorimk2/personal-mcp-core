# AI Worker Playbook

この文書は、AI development system の canonical parent
[`docs/architecture/ai-development-system.md`](./architecture/ai-development-system.md)
にぶら下がる **focused detail adapter** です。

> 関連 Issue: #373
> 関連 docs: [`docs/AI_WORKFLOW.md`](./AI_WORKFLOW.md), [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md), [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md), [`docs/WORKER_POLICY.md`](./WORKER_POLICY.md), [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md), [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md)

## 目的

AI worker が 1 つの Issue を受け取ってから、
着手、実装、検証、PR、review、handoff、中断、再開まで進む
**共通の標準作業フロー** を定義する。

この文書は runtime 固有のコマンドを定義しない。
「いつ着手できるか」「各フェーズで何を残すか」
「中断 / 再開 / handoff をどう成立させるか」を固定する。
development system 全体の topology や read order は parent doc を優先する。

## この文書が扱うこと / 扱わないこと

扱うこと:

- Issue 着手前確認から handoff までの共通フェーズ
- 各フェーズで最低限残す成果物
- 中断 / 再開 / handoff の成立条件
- claim protocol と registry をどこで参照するか

扱わないこと:

- worktree / branch / VSCode の配置ルール
- side-effect の許可 / 禁止
- runtime 別 CLI 手順や review コマンド
- claim protocol 自体の event 定義
- dispatch policy や runtime 選定ロジック

責務境界:

- 環境運用: [`docs/AI_WORKFLOW.md`](./AI_WORKFLOW.md)
- side-effect 境界: [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md)
- dispatch policy: [`docs/WORKER_POLICY.md`](./WORKER_POLICY.md)
- runtime 別手順: [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) などの runbook
- claim / release / handoff event: [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md)
- registry と GitHub の canonical source 境界: [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md)

## 着手条件

worker が作業を始めてよいのは、次を満たすときに限る。

- Issue の Goal / Scope / 受け入れ条件 / blocker が読める
- 現在の claim state が次のいずれかである
  - `unclaimed`
  - 自分が current owner である
  - 自分宛ての `handoff_accept` が成立している
- 自分の role と runtime が、その task-class を扱う前提に反していない
- 作業場所の前提が [`docs/AI_WORKFLOW.md`](./AI_WORKFLOW.md) と矛盾していない

着手不可の例:

- active claim が他 worker にある
- issue scope が不明で、仮定のまま進めると scope 逸脱になる
- handoff offer はあるが accept が成立していない

## 標準フェーズ

| Phase | 目的 | 確認すること | 最低限残すもの |
|---|---|---|---|
| 1. Intake | Issue を読む | Goal / Scope / AC / blocker / task-class | 何をやるかの短い要約、必要なら blocker |
| 2. Claim | ownership を明確にする | derived claim state、競合有無、handoff 受領可否 | `claim` または handoff 受領根拠 |
| 3. Plan | 変更方針を固定する | 触るファイル、検証方法、前提 docs | 短い plan、仮定、影響範囲 |
| 4. Execute | docs / code / review を進める | Issue scope 内か、正本と矛盾しないか | diff、変更ファイル、未解決点 |
| 5. Verify | 直近の失敗を潰す | 実行可能な検証コマンド、残リスク | 実行コマンド、結果、失敗理由 |
| 6. PR / Review | 他 worker / maintainer が読める形にする | linked issue、結果、残リスク、handoff 要否 | PR もしくは review package |
| 7. Release / Handoff | ownership を終える / 渡す | done / blocked / 別 worker 必要か | `release` または handoff record、次の一手 |

## フェーズごとの詳細

### 1. Intake

- Issue 本文、関連 docs、既存 PR / コメントを読む
- Goal / Scope / 受け入れ条件 / blocker を 3 から 6 行で要約する
- task-class と自分の role が噛み合わない場合は、claim せずに止まる

最低限残すもの:

- 作業対象の要約
- 不確実な点
- 着手不可なら blocker

### 2. Claim

- claim の正本は GitHub Issue 上の protocol record を使う
- `unclaimed` のときだけ新規 `claim` できる
- 自分が handoff target なら、`handoff_accept` 成立後に続行できる
- registry の `current_issue` は補助情報であり、claim の代わりにしない

最低限残すもの:

- `claim`、または自分が current owner だと分かる protocol record

### 3. Plan

- 変更対象、参照する正本、検証コマンド候補を決める
- Issue 外変更が必要そうなら、その時点で提案に留める
- claim protocol と dispatch policy をこの文書で再定義しない

最低限残すもの:

- 変更方針
- 仮定
- 検証方針

### 4. Execute

- 実装、docs 更新、review は Issue scope 内だけで進める
- registry は runtime observability の更新に使ってよいが、
  ownership 判定は GitHub 側 claim state を優先する
- 中断に備え、他 worker が読める粒度で進捗を残す

最低限残すもの:

- 変更ファイル
- 何を変えたか
- 未解決点または判断待ち

### 5. Verify

- 検証は runtime 別 runbook に従う
- 実行できなかった検証は「未実行」と理由を残す
- 失敗時は、直接関係する最小修正か、中断 / handoff のどちらかを選ぶ

最低限残すもの:

- 実行コマンド
- 成功 / 失敗
- 残リスク

### 6. PR / Review

- side-effect 担当 runtime は、必要な検証後に PR を作成する
- no-side-effect 担当 runtime は、diff / review package / 推奨コマンドを残す
- PR または handoff 文面には、linked issue、実行結果、残リスク、次の一手を含める

最低限残すもの:

- PR URL または review package
- linked issue
- 実行結果
- handoff 要否

### 7. Release / Handoff

- 完了したら current owner が `release` を残す
- 別 worker へ渡すときは `handoff_offer` を残し、target worker の `handoff_accept` で成立する
- offer だけでは ownership は移らない
- stale claim や abandoned handoff は maintainer override に委ねる

最低限残すもの:

- `release` または handoff record
- 次に見るべき PR / issue / doc
- blocker が残る場合は、その解除条件

## 中断 / 再開 / handoff

### 中断時に残す最小情報

中断時は、少なくとも次を残す。

- 現在の phase
- 変更したファイルまたは見た docs
- 直近の検証結果
- 未解決の blocker
- 次にやる 1 手
- ownership を手放すなら `release`
- ownership を渡したいなら `handoff_offer`

### 再開条件

再開前に次を確認する。

- claim state を見て、自分が current owner か、再度 `claim` 可能か
- 最新の PR / diff / コメント / review package を読んだか
- blocker が解消したか
- registry が示す runtime 状態は参考にしつつ、
  ownership 判定は GitHub 側 record に揃える

再開してよい例:

- 自分の claim がまだ active
- `release` 後に再度 `claim` した
- 自分宛ての handoff を `handoff_accept` した

再開してはいけない例:

- 他 worker の active claim がある
- handoff offer は見えているが accept していない
- 古い branch やローカル差分だけを根拠に ownership を主張する

### handoff の最小成立条件

handoff は次の順序で成立する。

1. current owner が `handoff_offer` を残す
2. target worker が `handoff_accept` を残す
3. target worker が次 phase に進む

handoff 文面または付随メモには、次を含める。

- 現在の phase
- 何が完了済みか
- 未完了の検証
- 見るべきファイル / PR / issue
- blocker と想定次アクション

## claim protocol への委譲

この文書は次を再定義しない。

- protocol event の厳密な field
- derived claim state の導出規則
- stale claim の override 条件

これらは [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md) を正本とする。

## registry への委譲

この文書は registry を ownership の正本にしない。

- worker の生存 / 進行状態は registry を参照してよい
- claim / handoff / override は GitHub 側 record を参照する
- 両者がずれた場合の優先順位は [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md) を正本とする

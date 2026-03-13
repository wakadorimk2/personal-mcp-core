# AI Worker Policy

> 関連 Issue: #374
> 関連 docs: [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md), [`docs/PLAYBOOK.md`](./PLAYBOOK.md), [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md), [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md)

## 目的

multi-runtime 環境で、
どの task-class をどの runtime に優先的に割り当てるか、
どの順で collision を避けるか、
implementer と reviewer をどう分離するかを定義する。

この文書は dispatch policy の正本であり、
副作用の許可 / 禁止、claim protocol の event 定義、runtime 固有コマンドは再定義しない。

## この文書が扱うこと / 扱わないこと

扱うこと:

- task-class ごとの preferred runtime と fallback の考え方
- dispatch の確認順序
- collision avoidance の原則
- implementer と reviewer の分離原則
- maintainer override が必要になる条件

扱わないこと:

- side-effect 境界そのもの
- claim / release / handoff event の形式
- worktree / branch / VSCode の運用
- runtime ごとの CLI / review / PR コマンド
- scheduler や bot による自動 dispatch

責務境界:

- side-effect 境界: [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md)
- 共通作業フロー: [`docs/PLAYBOOK.md`](./PLAYBOOK.md)
- claim / handoff の canonical event log: [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md)
- registry と GitHub の canonical source 境界: [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md)

## dispatch 対象にしてよい runtime

baseline では、次を満たす runtime だけを dispatch 対象にする。

- repo-wide entrypoint と read order を辿れる
- role boundary 上の担当が定義されている
- runtime-specific runbook または同等の制約文書がある

この条件を満たさない runtime は、
実験的な補助用途には使えても、
preferred runtime / fallback runtime の baseline 対象には含めない。

現時点の baseline:

- Claude Code: no-side-effect 側
- Codex CLI: side-effect 側
- Copilot など未整備 runtime: manual override があるときだけ個別判断

## task-class matrix

| task-class | 目的 | preferred runtime | fallback | prerequisites |
|---|---|---|---|---|
| `research` | 論点整理、設計案、比較、Issue 化前の調査 | Claude Code | Codex CLI | 副作用なしで完結できる |
| `implementation-diff` | Issue スコープ内の diff / docs 変更案を作る | Claude Code | なし | no-side-effect 側で扱えること |
| `verification` | review、lint、test、最小修正、PR 作成 | Codex CLI | なし | side-effect 側 runbook で実行可能 |
| `review` | 適用済み差分の検査と報告 | Codex CLI | Claude Code | 必要な検査が role boundary と矛盾しない |
| `ops-docs` | runbook / workflow / orchestration docs の同期 | Codex CLI | Claude Code | 副作用要否を先に切り分ける |

fallback の読み方:

- fallback は「preferred が使えないときに自動で使う相手」ではなく、
  role boundary と前提 docs を満たす場合に限る次善候補を意味する
- `なし` は、その task-class を baseline では別 runtime に委譲しないことを意味する

## dispatch の確認順序

dispatch は次の順で判断する。

1. task-class を決める
2. [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md) で、その task-class が no-side-effect 側か side-effect 側かを確認する
3. [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md) の derived claim state を見て、active owner の有無を確認する
4. active claim がなければ preferred runtime を選ぶ
5. preferred runtime が利用不可なら、fallback の前提を満たすか確認する
6. fallback も使えなければ、人間 Maintainer が manual dispatch または優先度見直しを行う

確認順の原則:

- `GitHub claim -> registry observability` の順で見る
- registry は availability / liveness の補助情報として使う
- registry の `current_issue` だけで ownership を判定しない

## collision avoidance

worker が着手前に確認する最小ルールは次のとおり。

- active claim が他 worker にあるなら着手しない
- `handoff_pending` は current owner がまだ元 worker である前提で扱う
- competing claim が見えたら、後続 worker は進めず maintainer 判断に戻す
- registry で runtime が `idle` に見えても、GitHub claim が active なら空きとはみなさない
- task-class が切り替わるときも、claim state と handoff 成立を先に確認する

## implementer / reviewer 分離原則

原則:

- implementer と reviewer は別 runtime に分ける
- no-side-effect 側が作った diff は、side-effect 側が検証して PR 化する
- side-effect 側が最小修正を入れた場合も、修正理由は review 文脈で説明可能であることを要件にする

baseline の対応:

- Claude Code が `research` / `implementation-diff` を担当する
- Codex CLI が `verification` / `review` / PR 作成を担当する

例外を許す条件:

- 利用可能な runtime が 1 つしかない
- docs-only で副作用のない review を短時間で閉じたい
- 緊急修正で reviewer 分離より停止時間の短縮を優先する

例外時に残すもの:

- なぜ分離できなかったか
- どの検証を省略していないか
- maintainer が後から確認すべき点

## preferred / fallback の詳細ルール

### `research`

- preferred は Claude Code とする
- 既存 skill や diff 提案フローが no-side-effect 前提で揃っているため
- Codex CLI を使うのは、side-effect を伴わない範囲で補助的に整理するときに限る

### `implementation-diff`

- preferred は Claude Code とする
- baseline では feature 実装や docs 変更案の一次生成を no-side-effect 側に寄せる
- side-effect 側は検証起因の最小修正に留め、仕様追加の implementer にはしない

### `verification`

- preferred は Codex CLI とする
- `ruff` / `pytest` / review / PR 作成は side-effect 側 runbook に沿って扱う
- fallback は置かず、使えない場合は maintainer が別手段を指示する

### `review`

- preferred は Codex CLI とする
- ただし実行を伴わない docs review や論点整理レビューは Claude Code に委譲してよい
- その場合でも最終的な merge 判断は maintainer が持つ

### `ops-docs`

- orchestration / runbook / workflow docs は Codex CLI を preferred とする
- 既存 docs とのリンク整合、検証、PR 整形まで含めやすいため
- ただし文章草案や論点抽出は Claude Code へ handoff してよい

## manual override が必要なとき

次のケースでは、maintainer が manual dispatch または override を判断する。

- preferred / fallback のどちらも role boundary に反する
- active claim が stale だが current owner が `release` できない
- 複数 runtime が competing claim を残している
- task-class の切り方自体が曖昧で、dispatch すると scope 逸脱になりうる
- reviewer 分離を守れず、その例外を当人だけで正当化しきれない

## playbook / claim / registry への委譲

この文書は次を再定義しない。

- claim event の field と derived state 算出規則
- handoff の成立条件そのもの
- 中断 / 再開時に残す作業ログの最小項目
- registry event schema や dashboard 表示形式

これらは次を正本とする。

- [`docs/worker-claim-protocol.md`](./worker-claim-protocol.md)
- [`docs/PLAYBOOK.md`](./PLAYBOOK.md)
- [`docs/worker-registry-coordination.md`](./worker-registry-coordination.md)

## 運用メモ

- preferred runtime は能力ランキングではなく、現在の role boundary と runbook 整備状況に基づく
- future runtime を追加するときは、この文書だけでなく role boundary と runbook の整備を先に行う
- dispatch policy は人間 Maintainer の判断を置き換えない

# AI Workflow (Git / worktree / VSCode)

この文書は、AI development system の canonical parent
[`docs/architecture/ai-development-system.md`](./architecture/ai-development-system.md)
にぶら下がる **focused detail adapter** です。

この文書に残すもの:

- worktree / branch / VSCode 運用の detail
- daily operational checks
- 現時点で parent doc に吸収していない local appendix

副作用権限の detail は [docs/AI_ROLE_POLICY.md](./AI_ROLE_POLICY.md)、
Issue 着手から handoff までの phase flow detail は [docs/PLAYBOOK.md](./PLAYBOOK.md) を参照します。
本書は作業場所と運用手順に限定します。
他の docs 導線は [`docs/README.md`](./README.md) を参照します。

---

## Goal

- worktree の役割を固定する
- branch を task 単位で短命運用する
- VSCode の作業机を固定し、戻り先を明確にする
- AI worker の責務境界を最小限で共有する

---

## 1. Worktree ルール

原則:

- worktree は `長期 / 役割ベース`
- branch は `短命 / taskベース`
- 長期 branch は持たない

推奨構成（4 worktree）:

```text
personal-mcp-core          (human)
personal-mcp-core-advisor
personal-mcp-core-builder
personal-mcp-core-ops
```

最小構成（2 worktree）:

```text
personal-mcp-core          (human)
personal-mcp-core-builder
```

`advisor` と `ops` を同一 worktree に統合してもよいが、同時並行作業が増えたら分離する。

---

## 2. Branch 運用ルール

命名:

- `docs/<YYYY-MM-DD>-<topic>`
- `feat/<YYYY-MM-DD>-<topic>`
- `fix/<YYYY-MM-DD>-<topic>`
- `ops/<YYYY-MM-DD>-<topic>`

運用:

- 1 task = 1 branch
- branch は `origin/main` 起点で作成する
- merge 後は local / remote の branch を削除する
- 長期の作業継続は branch ではなく worktree 側で吸収する

---

## 3. Parking 状態（待機状態）

各 worktree の待機状態を以下に固定する。

- branch: `main`
- working tree: clean (`git status --short` が空)
- リモート同期: `origin/main` と fast-forward 可能

`detached HEAD` は待機状態として使わない。

---

## 4. VSCode 作業机の固定

VSCode は worktree 単位で 1 ウィンドウを固定する。

```text
human   -> personal-mcp-core
advisor -> personal-mcp-core-advisor
builder -> personal-mcp-core-builder
ops     -> personal-mcp-core-ops
```

運用ルール:

- 同一ウィンドウで別 worktree に移動しない
- task 切替時は branch を切り替える前に対象 window/worktree を確認する
- window 名に role を含める（例: `builder: personal-mcp-core-builder`）

補足（ローカル運用）:

- `human` 用ウィンドウ 1 つから、VSCode task で `advisor / builder / ops` 用 terminal を追加起動する運用は許容する
- ただし、起動先ディレクトリや CLI コマンドはローカル依存が強いため、`.vscode/tasks.json` は repo で管理しない（各自ローカルで保持する）
- repo には運用原則（worktree / branch / role 境界）のみを残し、task 定義の具体値は配布対象にしない

---

## 5. AI worker の責務境界

`advisor`:

- 調査
- 論点整理
- 設計メモ
- docs 提案

`builder`:

- 実装
- small patch
- テスト

`ops`:

- issue 作成 / 更新
- PR 整形
- labels / project 整理
- runbook / workflow docs 更新

補足:

- 上記は「作業レーン」の責務であり、副作用の可否判定は `AI_ROLE_POLICY` を優先する

---

## 6. Daily チェック（最小）

作業開始時に実行:

```bash
git status --short --branch
git branch --show-current
git fetch -p origin
```

確認項目:

- 期待した worktree / branch で作業している
- 意図しない差分がない
- `main` 起点の新規 task branch を作成できる状態である

---

## 6.1 Branch cleanup quick reference

branch cleanup は独立 cheatsheet ではなく、この文書の operational appendix として扱う。

新しい branch を作るとき:

```bash
git fetch origin
git switch -c feat/<topic> origin/main
```

削除可否を見るとき:

```bash
git branch -vv
git rev-list --left-right --count main...origin/<branch-name>
git diff --stat $(git merge-base main origin/<branch-name>)..origin/<branch-name>
git log --oneline --decorate --graph main..origin/<branch-name>
```

判断の目安:

- branch 側コミット数が `0` なら削除候補
- 実差分が空なら、古い base branch や role branch の可能性が高い
- `log` は履歴差、`diff` は実体差として読む

削除コマンド:

```bash
git push origin --delete <branch-name>
git branch -d <branch-name>
git fetch --prune
```

原則:

- branch の役割は worktree 名で表す
- 長寿命 base branch は延命しない
- 削除は手動確認ベースで行う

---

## 7. GitHub Project Active管理ルール（試行）

この節は、`#417` 時点では canonical parent に吸収していない
**local appendix** として残す。
development system 全体の topology ではなく、現行の ops 運用メモとして扱う。

この節は、Project を「TODO 一覧」ではなく「active management の作業面」にするための最小ルールを定義する。
試行期間は **2026-03-09 から 2026-03-22（2週間）** とし、期間後に閾値と運用を見直す。

### 7.1 基本原則

- Project は `active management 用` として使う
- `Project外デフォルト` とし、backlog は基本的に Project に載せない
- Priority を付与する対象は `Project内かつ active/ready` の Issue のみ
- Priority は backlog 全体には付与しない（情報価値を落とさないため）

### 7.2 14日ルール

- 次の条件を満たす Issue は Project から外す
  - 最終更新または運用ログ更新から 14 日以上経過
  - 直近の次アクションが定義されていない
- 外す際は Issue 本文またはコメントに `戻し条件` を 1 行残す
  - 例: `再投入条件: blocker解除後に active 化`

### 7.3 Epic の扱い

- Epic は active child が 1 件以上ある間、Project に残す
- Epic は実装実体ではなく、`観測ログ` と `意思決定履歴` の集約先として運用する
- child がすべて backlog/out になったら Epic も 14 日ルールの対象にする

### 7.4 依存メタデータの使い分け

- `parent-child`: 実行順序を持つ分割タスクの束を表す（Epic と子 Issue）
- `blocked-by`: 直接の着手阻害要因を表す（解除されるまで active にしない）
- `refs`: 文脈参照のみを表す（依存関係として扱わない）

### 7.5 WIP 上限

- Implementation: 2
- Decision-design: 1
- Ops-workflow: 1
- 合計上限: 4

上限超過時は `新規投入` ではなく `既存 active の完了/棚卸し` を先に行う。

### 7.6 代表 Issue のサンプル判定（2026-03-09 時点）

| Issue | 判定 | Project扱い | Priority |
|---|---|---|---|
| #174 Epic: 日常ログ UX 探索 | 残す | `active child あり` の間は保持。観測/意思決定ログの親として運用 | 付与しない |
| #180 daily input UX 最小導線 | 残す | active/ready 候補（Implementation） | 付与対象 |
| #185 dual-write 方針整理 | 残す | active/ready 候補（Decision-design） | 付与対象 |
| #189 storage abstraction | 残す | active/ready 候補（Implementation） | 付与対象 |
| #190 migration tool | 外す（backlog） | #189 完了まで待機。必要時に再投入 | 付与しない |
| #191 dual-write 撤去 | 外す（backlog） | #190 以降で再評価 | 付与しない |
| #177 Makefile 日常運用整備 | 残す | active/ready 候補（Ops-workflow） | 付与対象 |
| #150 外部保存戦略（GCP候補） | 外す（backlog） | 参照情報として保持。着手条件成立時に再投入 | 付与しない |

### 7.7 週次20分トリアージ（最小チェック）

- 1. Project 内 Issue が WIP 上限（Implementation 2 / Decision-design 1 / Ops-workflow 1 / 合計 4）を超えていないか
- 2. `active/ready` 以外に Priority が付いていないか
- 3. 14 日以上更新がない Issue に `残す理由` または `外す判断` があるか
- 4. Epic が child 状態と整合しているか（child なしなのに残置していないか）
- 5. `blocked-by` と `refs` が混在して依存解釈を誤らない状態か

### 7.8 試行運用ログの残し方（2026-03-09〜2026-03-22）

- 毎週 1 回、20 分で 7.7 を実施する
- 変更時は Issue コメントに `判定（残す/外す/再投入）` と `理由` を 1-2 行で記録する
- 試行期間終了時に次を見直す
  - WIP 上限の妥当性
  - 14 日閾値の妥当性
  - Priority 対象範囲（active/ready 限定）の維持可否

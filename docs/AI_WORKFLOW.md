# AI Workflow (Git / worktree / VSCode)

この文書は、AI worker を含む開発の最小運用ルールを定義する。
副作用権限（Claude/Codex の境界）は [docs/AI_ROLE_POLICY.md](./AI_ROLE_POLICY.md) を正本とし、
本書は作業場所と運用手順に限定する。

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

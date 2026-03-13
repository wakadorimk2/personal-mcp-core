# CODEX_RUNBOOK

この文書は [`docs/RUNBOOK_BASELINE.md`](./RUNBOOK_BASELINE.md) で定義した runtime-specific runbook baseline の exemplar（Codex CLI 用）です。

Codex はこの runbook に従って、`review -> ruff -> pytest -> 最小修正 -> 再実行 -> Draft PR` の順で進む。役割境界の正本は [docs/AI_ROLE_POLICY.md](./AI_ROLE_POLICY.md) とし、この文書は実行手順に絞る。
Repo-wide AI entrypoint は [`AGENTS.md`](../AGENTS.md) です。Codex はまず `AGENTS.md` で read order と precedence を確認し、その後この runbook を使います。Issue 着手から handoff までの共通進行管理は [`docs/PLAYBOOK.md`](./PLAYBOOK.md)、runtime 間の dispatch policy は [`docs/WORKER_POLICY.md`](./WORKER_POLICY.md) を正本とし、この文書では再定義しません。
他の docs 導線は [`docs/README.md`](./README.md) を参照する。

## Codex がやること

- 既存差分の review
- `ruff` / `pytest` の実行
- 検証で確認できた失敗に対する最小修正
- `gh` による Draft PR 作成

## Codex がやってはいけないこと

- 仕様追加、設計変更、Issue スコープ拡張
- 依存追加、大規模リファクタ、広範囲の整形
- テスト無効化、閾値緩和、失敗の握りつぶし
- `main` 直編集、誤った remote への push、秘密情報の貼り付け

上記が必要になったら止まり、別 Issue 案だけを残す。

## 停止条件

- `git status` が意図しない差分を含む
- 現在ブランチが `main`
- `ruff` / `pytest` 失敗の解消に設計変更が要る
- 同じ失敗の再実行が 3 回で収束しない
- 最小修正が 2 サイクルを超える
- `gh` 認証、権限、remote の問題で PR が作れない
- 役割境界文書の優先順位が解決できず、実行可否が判断不能

## 境界変更同期チェック（policy/runbook 系 Issue）

`AGENTS.md`・`docs/AI_ROLE_POLICY.md`・`AI_GUIDE.md`・`CLAUDE.md`・`docs/CODEX_RUNBOOK.md`・skill adapters をまたぐ Issue では、
Standard Flow の前に次のチェックポイントを実施する。

| Checkpoint | 完了条件 | 次ステップ進行条件 | 停止条件 |
|---|---|---|---|
| 1. 正本 | `docs/AI_ROLE_POLICY.md`（必要時 `docs/skills/*.md` canonical）で境界変更が確定している | 差分または既存 commit で Step 1 完了を確認できる | 導線/配布物だけ先に更新され、正本が未確定 |
| 2. 導線 | `AI_GUIDE.md` / `CLAUDE.md` が正本参照と矛盾時導線を保持している | Step 1 と矛盾しないことを確認できる | 正本と導線の矛盾が残る |
| 3. skills/runbook | `docs/CODEX_RUNBOOK.md` / remaining canonical skill docs / `.codex/skills/*` / `.claude/skills/*` が Step 1/2 と一致 | Step 1/2 の完了後に同期差分のみを反映する | Step 1/2 未完了のまま実行手順や配布物だけ更新する |

矛盾発生時の暫定運用:

- `正本 > 導線 > skills/runbook > 過去 Issue/コメント` の順で判断する
- 副作用可否や停止条件に影響する矛盾は、作業を停止して Maintainer にエスカレーションする
- 運用判断に影響しない文言差は正本基準で進め、follow-up Issue で同期漏れを解消する

## review-preflight skill との関係

`review-preflight` skill（本書の Appendix B を参照）は
**検査と報告のみ** を責務とし、修正を行わない。

この runbook の Standard Flow（Step 5 Minimal Fix を含む）は、`review-preflight` による
preflight 完了後に Codex が実施する実行フローである。両者を混同しない。

| 項目 | review-preflight skill | この runbook の Standard Flow |
|---|---|---|
| 修正 | 行わない | 局所・可逆な最小修正のみ許容 |
| 4 観点チェック | 実施する（Contract / Scope / Migration / Docs-Impl） | 対象外 |
| 自動修正ループ | 禁止 | 最大 2 サイクル、3 回収束しなければ停止 |
| 出力形式 | `Summary / Preflight Checks / Failures / Next Step` | Draft PR 本文（PR Body Template） |

## Standard Flow

### 1. Safety Check

目的: 誤爆防止。対象 repo、作業ツリー、作業ブランチを確認する。

コマンド例:

```bash
git remote -v
git status --short --branch
git branch --show-current
```

期待結果: `origin` が対象 repo、意図しない差分なし、現在ブランチが `main` ではない。

次に進む条件: 安全確認が取れた。

停止条件: remote 誤り、不要差分あり、`main` 上での作業。

`git pull` / `git merge` / `git rebase` を実行するときは、誤 worktree 混入を避けるため
`scripts/codex_git_guard.py` を前段に置く。

コマンド例:

```bash
python scripts/codex_git_guard.py \
  --expect-role ops \
  --expect-worktree /home/you/projects/pmc-ops \
  --expect-branch main \
  --expect-remote origin \
  -- pull
```

失敗時:

- 標準エラーに `role/worktree/current branch/target branch/remote/clean tree` のどこが不一致か出る
- `recovery:` に従って正しい worktree / branch へ戻ってから再実行する

bypass が必要な場合:

```bash
PMC_GIT_GUARD_BYPASS=1 python scripts/codex_git_guard.py -- pull origin main
```

- bypass は one-off のみとし、理由を PR または作業メモに残す
- 常用 alias や環境変数 export での恒久 bypass はしない

### 2. Review

目的: 変更意図、リスク、確認対象を短く把握する。

コマンド例:

```bash
git status --short
git diff --stat
git diff
```

期待結果: 何を変えたか、どこが壊れ得るか、どのファイルを見るべきかを 3 点以内で説明できる。

次に進む条件: Issue スコープ内であると判断できる。

停止条件: Issue 外変更、仕様追加、広範囲修正が混ざっている。

### 3. Ruff

目的: lint / import / format 系の失敗を先に潰す。

Ruff 設定の正本は `pyproject.toml` とする。
`ruff check .` は lint rule failure を示し、`E501` を ignore していない限り line-length violation を含みうる。
`ruff format --check .` は formatting drift を示し、line-length 設定の CLI 上書き有無とは別に読む。

コマンド例:

```bash
ruff --version
ruff check .
ruff format --check .
```

期待結果: `ruff check .` と `ruff format --check .` が成功する。失敗時は対象ファイルと rule / formatting drift が特定できる。

次に進む条件: 成功、または最小修正で収まりそうと判断できる。

停止条件: 自動修正や局所修正では収まらず、設計変更や広範囲整形が必要。

### 4. Pytest

目的: 挙動 regressions を確認する。

コマンド例:

```bash
python --version
pytest --version
pytest
```

期待結果: 全テスト成功。失敗時は再現手順、失敗箇所、環境差の有無を説明できる。

次に進む条件: 成功、または最小修正で収まりそうと判断できる。

停止条件: 仕様変更が必要、再現しない、環境依存が強く切り分け不能。

補足: `web-serve` と `summary-generate` を手動検証するときは、同じ `DATA_DIR` を必ず使う。

```bash
# 共通 data directory（ここで一度だけ作る）
# 別ターミナルで mktemp -d を再実行しないこと
export DATA_DIR="$(mktemp -d)"
export DATE="$(date -u +%F)"

echo "DATA_DIR=$DATA_DIR"
echo "DATE=$DATE"

# start server
python -m personal_mcp.server web-serve \
  --data-dir "$DATA_DIR" \
  --port 8080
```

別ターミナル:

```bash
source .venv/bin/activate

curl -sS -X POST "http://localhost:8080/events" \
  -H "Content-Type: application/json" \
  -d '{"domain":"mood","kind":"note","text":"手動確認イベント"}'

python -m personal_mcp.server summary-generate \
  --date "$DATE" \
  --annotation "初回" \
  --interpretation "確認用" \
  --data-dir "$DATA_DIR" \
  --json

curl -sS "http://localhost:8080/summaries?date=$DATE"
```

### 5. Minimal Fix

目的: 検証で確認できた失敗だけを、局所・可逆・説明可能な範囲で直す。

コマンド例:

```bash
git diff
```

期待結果: 修正が失敗箇所に直接対応し、1 から 2 ファイル程度に収まる。

次に進む条件: 修正理由を 1 文で説明できる。

停止条件: 依存追加、設計変更、広範囲修正、最小修正 2 サイクル超過。

### 6. Re-run

目的: 修正後の収束確認。

コマンド例:

```bash
ruff check .
pytest
```

期待結果: `ruff` → `pytest` の順で成功する。

次に進む条件: 両方成功。

停止条件: 同じ失敗の再実行が 3 回で収束しない。

### 7. Commit

目的: 単一関心の変更として記録する。

コマンド例:

```bash
git add docs/CODEX_RUNBOOK.md
git commit -m "docs: add CODEX_RUNBOOK for executor flow"
```

期待結果: runbook 追加だけがコミットされる。

次に進む条件: コミット成功。

停止条件: 追加で混入した差分を分離できない。

### 8. Draft PR

目的: 実行結果と残リスクを残してレビューに渡す。

linked issue ルール:

- 対応 Issue を PR 本文に 1 件以上明記する
- merge 時に Issue を閉じる場合は `Closes #<issue-number>` / `Fixes #<issue-number>` / `Resolves #<issue-number>` を使う
- merge 時に閉じない場合は `Refs #<issue-number>` を書き、必要なら GitHub 上で linked issue を手動設定する
- PR title 末尾の `(#123)` や本文中の単なる `#123` 記載だけでは linked issue とみなさない

コマンド例:

```bash
gh pr create --draft --title "docs: add Codex executor runbook" --body-file <(cat <<'EOF'
<PR Body Template を埋めて貼る>
EOF
)
```

期待結果: Draft PR が作成され、本文に実行結果と環境情報が入る。

次に進む条件: PR URL を取得できる。

停止条件: `gh auth` 未設定、権限不足、base/head 誤り。

## Failure Branches

- Lint / format 失敗: `ruff` の対象ルールとファイルを確認する。局所修正で済むなら 1 回直して `ruff check .` を再実行する。広がるなら停止。
- Import / type 失敗: import path、未使用 import、単純な型不整合だけを直す。公開 API や設計変更が要るなら停止。
- Test 失敗: 失敗テスト名と例外を確認し、最短で再現する。局所修正後は `ruff check .` からやり直す。
- Flake 疑い: 同じコマンドの再実行は最大 3 回。3 回で収束しなければ flake として記録し、隔離や安定化は別 Issue。
- 環境差: `python --version`、`ruff --version`、`pytest --version` を残す。OS や依存差が原因なら PR に記載して停止。
- `gh` 失敗: `gh auth status`、`git remote -v`、現在ブランチを確認する。認証や権限の問題は解消せずに状況を報告して止まる。

## PR Body Template

```md
## 関連Issue
- Closes #<issue-number>
<!-- close しない場合は `Refs #<issue-number>` に置き換え、必要なら linked issue を手動設定する -->

## 概要
- 変更内容:
- 理由:

## 検証
- python: `<python --version>`
- ruff: `<ruff --version>`
- pytest: `<pytest --version>`
- `ruff check .`: `<pass/fail>`
- `pytest`: `<pass/fail>`

## レビューノート
- スコープ:
- 挙動変更:
- リスク:
- 緩和策:

## 最小修正
- 適用内容:
- 理由:

## 次のIssue
- なし / <後続 issue 候補>
```

## 完了時に残すもの

- PR リンク
- 実行したコマンドと結果
- 残リスク
- 別 Issue 化すべき事項があれば箇条書き

## Skill-backed appendices

この runbook は、日常運用で高頻度に参照される skill spec を吸収している。
以下は独立 docs ではなく、本書を canonical source とする。

- `review-diff`
- `review-preflight`
- `minimal-safe-impl`
- `issue-create`
- `issue-project-meta`

### Appendix A. review-diff

目的:

- diff review の観点と出力順を固定する
- findings を summary より先に、HIGH から LOW の順で並べる

Procedure:

1. diff context を集める
2. diff を 2 から 5 行で要約する
3. 影響度順にファイルを並べる
4. 各ファイルを `regression / scope deviation / missing tests` の 3 観点で見る
5. finding を `HIGH -> MEDIUM -> LOW` で列挙する
6. 根拠が不足する点は `Open Questions` に回す

Output:

- `## Findings`
- `## Open Questions`
- `## Change Summary`
- `## Next Step`

Constraints:

- 根拠がない指摘を断定しない
- review scope 外の推測を広げない
- `ruff` / `pytest` 失敗が見えても、自動修正には進まない

### Appendix B. review-preflight

目的:

- merge 前 review の検査順と報告形式を固定する
- 修正を行わず、検査と報告だけに責務を限定する

Fixed Procedure:

1. `git status --short --branch`
2. `git diff --stat`
3. `ruff check .`
4. `pytest`
5. `contract / scope / migration / docs-impl` の 4 観点チェック
6. Markdown report を出す

Output:

- `## Summary`
- `## Preflight Checks`
- `## Failures`
- `## Next Step`

Rules:

- 修正しない
- 自動再試行しない
- `Next Step` では修正先を 1 行で示すだけに留める

### Appendix C. minimal-safe-impl

目的:

- MVP 互換性ポリシーに従って、Issue scope 内の最小差分実装を行う

Rules:

- Scope 外の refactor / rename / formatting-only 修正を入れない
- 既存のディレクトリ構造・CLI パターンを踏襲する
- 恒久互換レイヤや「あとで必要かもしれない」拡張点を追加しない
- データ形式変更が必要なら移行を同伴し、恒久互換レイヤは作らない

Output:

- 実装方針
- 変更ファイル一覧
- 実行コマンド
- 仮定
- 完了チェック

### Appendix D. issue-create

目的:

- `issue-draft` 済みの title/body から、再実行可能な GitHub Issue 作成手順を固定する

Fixed Procedure:

1. `issue-draft` 完了を確認する
2. `gh label list --json name --jq '.[].name'` でラベル存在確認を行う
3. 重複疑い時は `gh issue list --search` で検索する
4. `gh issue create --body-file` 形式のコマンドを生成する
5. URL / 番号 / labels / 作成日時を記録する

Rules:

- 実行前にラベル存在確認を省略しない
- 重複疑いがあるときは検索を飛ばさない
- Project / relationship 更新は Appendix E に委譲する

Output:

- ラベル確認コマンド
- 重複チェックコマンド
- `gh issue create` コマンド
- 作成結果記録

### Appendix E. issue-project-meta

目的:

- Issue 作成後に Project item / Status / Priority / dependency metadata を反映する

Fixed Procedure:

1. Issue URL / 番号が確定していることを確認する
2. `gh project list` / `gh project field-list` / `gh project item-list` で必要な ID を取得する
3. `gh project item-add` を行う
4. 必要なら `gh project item-edit` で Status / Priority を更新する
5. 必要なら blocked-by / sub-issue を API で反映する
6. Result / TODO / Rationale を記録する

Rules:

- Issue 作成前に実行しない
- 根拠なしで Status / Priority を更新しない
- 未実施項目を隠さず `TODO` に残す

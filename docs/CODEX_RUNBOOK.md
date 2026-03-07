# CODEX_RUNBOOK

Codex はこの runbook に従って、`review -> ruff -> pytest -> 最小修正 -> 再実行 -> Draft PR` の順で進む。役割境界の正本は [docs/AI_ROLE_POLICY.md](./AI_ROLE_POLICY.md) とし、この文書は実行手順に絞る。

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

## review-preflight skill との関係

`review-preflight` skill（[`docs/skills/review-preflight.md`](./skills/review-preflight.md)）は
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

コマンド例:

```bash
ruff --version
ruff check .
```

期待結果: `ruff check .` が成功する。失敗時は対象ファイルとルールが特定できる。

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
## Summary
- What changed:
- Why:

## Validation
- python: `<python --version>`
- ruff: `<ruff --version>`
- pytest: `<pytest --version>`
- `ruff check .`: `<pass/fail>`
- `pytest`: `<pass/fail>`

## Review Notes
- Scope:
- Behavior change:
- Risks:
- Mitigation:

## Minimal Fix
- Applied:
- Reason:

## Next Issues
- None / <follow-up issue candidate>
```

## 完了時に残すもの

- PR リンク
- 実行したコマンドと結果
- 残リスク
- 別 Issue 化すべき事項があれば箇条書き

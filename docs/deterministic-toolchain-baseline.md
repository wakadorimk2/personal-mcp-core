# Deterministic Toolchain Baseline — Issue #260

> 種別: 棚卸し / 方針整理
> 親 Issue: #259
> 更新日: 2026-03-09

---

## Goal

`personal-mcp-core` における deterministic guardrail の現状を棚卸しし、
型、lint、format、AST/構造チェック、repo exploration tooling を
どの面で使う候補かを固定する。

この文書は baseline と導入順の整理を扱い、各 tool の導入実装は扱わない。

## Non-goal

- CI 設定や pre-commit の追加
- 型ルール、lint ルール、formatter 設定値の詳細確定
- structural constraints や cleanup pipeline の実装

## 現在の deterministic baseline

現時点で repo 内に存在する deterministic guardrail は次のとおり。

| area | current state | run surface | failure meaning | source |
|---|---|---|---|---|
| test | `pytest` を `make test` と `docs/CODEX_RUNBOOK.md` で実行する | local preflight / review 前検証 | 既存挙動 regressions の疑い | `Makefile`, `docs/CODEX_RUNBOOK.md` |
| lint | `ruff check .` を `make lint` で実行する。現状ルールは `E`, `F` の最小集合 | local preflight / review 前検証 | syntax, import, 未使用、基本的な静的ミスの疑い | `pyproject.toml`, `Makefile`, `docs/CODEX_RUNBOOK.md` |
| format | `ruff format .` を `make fmt` で実行できる | local manual fix | formatting drift | `pyproject.toml`, `Makefile` |
| guide sync | `make guide-check` で `AI_GUIDE.md` と package copy の同期を確認できる | local preflight / docs change review | docs 配布物の drift | `Makefile` |
| repo exploration | `rg`, `git diff`, `gh issue view`, `scripts/issue_dag.py` で repo と issue graph を機械的に探索できる | review 補助 / issue triage | 読み漏れ・依存関係の見落としを減らす | `docs/CODEX_RUNBOOK.md`, `Makefile`, `scripts/issue_dag.py` |
| execution safety | `docs/CODEX_RUNBOOK.md` の Safety Check と `#208` の launch guard 方針がある | local preflight | 誤 worktree / branch 実行の疑い | `docs/CODEX_RUNBOOK.md`, `#208` |

補足:

- baseline はすでに存在するが、`lint` `format` `type` `AST/構造` `repo exploration` が
  1 枚に整理されていなかった
- `ruff format .` は書き換えコマンドなので、CI に置く場合は `ruff format --check .` に分けるのが自然
- `#208` は quality checker ではなく、誤爆防止 guardrail として別軸で併置する

## カテゴリ別比較

### 1. Type checking

| option | purpose | execution surface | failure meaning | introduction cost | notes |
|---|---|---|---|---|---|
| `mypy` | 既存コードに対して gradual に型の穴を見つける | local preflight -> CI 候補 | annotation 不足、型不整合、戻り値や `Optional` の崩れ | 中 | Python repo にそのまま追加しやすく、`pyproject.toml` で段階導入しやすい |
| `pyright` / `basedpyright` | より強い型診断、IDE 連携を含む型検査 | local preflight -> CI 候補 | `mypy` と同様だが診断の粒度や挙動は別 | 中 | 候補として有効だが、初手で複数 checker を持つ必要は薄い |

現状判断:

- 初手候補は `mypy` を優先案として扱う
- 理由は、repo の開発導線が `make setup -> pip install -e ".[dev]"` で揃っており、
  Python 依存だけで足しやすいこと
- `pyright` / `basedpyright` は follow-up 比較対象として残すが、
  baseline Issue の時点では「型 checker を 1 つ導入する」ことの方が重要

### 2. Lint

| option | purpose | execution surface | failure meaning | introduction cost | notes |
|---|---|---|---|---|---|
| 現状 `ruff check .` (`E`, `F`) | syntax / import / 未使用などの基本 guardrail | local preflight / CI 候補 | 明確な静的ミス | 低 | すでに導線あり。baseline の核 |
| `ruff` ルール拡張 (`I`, `B`, `UP`, `SIM` など) | import 順、bug-prone pattern、古い書き方の検出 | local preflight -> CI 候補 | style ではなく maintainability / bug-risk の検出 | 中 | 一気に広げると既存差分が増えるため、初手導入には向かない |

現状判断:

- baseline は現状の `ruff check .` をそのまま guardrail として固定する
- follow-up では `I` と `B` のような「失敗理由が説明しやすいルール群」から段階追加する案が扱いやすい

### 3. Format

| option | purpose | execution surface | failure meaning | introduction cost | notes |
|---|---|---|---|---|---|
| `ruff format .` | ローカルで整形を一括適用する | local manual fix | formatting drift | 低 | すでに `make fmt` がある |
| `ruff format --check .` | 非破壊で formatting drift を検知する | local preflight / CI 候補 | 整形未適用 | 低 | CI / review 前検査に向く |

現状判断:

- format は「新規ツール候補」ではなく「既存ツールの実行面の固定」が主題
- local manual fix は `make fmt`、非破壊検査は `ruff format --check .` で分けるのが自然

### 4. AST / structural rules

| option | purpose | execution surface | failure meaning | introduction cost | notes |
|---|---|---|---|---|---|
| `ast-grep` | AST ベースで構造パターンを検出し、repo 固有ルールを明示する | local preflight / CI 候補 | 文法上は正しいが、repo で禁じたい構造の混入 | 中 | structural constraints の follow-up と相性がよい |
| `semgrep` | ルールベース検査を広く行う | local preflight / CI 候補 | AST/パターン違反、セキュリティ系規約違反 | 中〜高 | 射程は広いが、`personal-mcp-core` の初手用途としてはやや広い |

現状判断:

- structural constraints 用の初手候補は `ast-grep` を優先案として残す
- 理由は、Issue #260 の主眼が security scanner 導入ではなく
  repo 固有の構造 guardrail を deterministic に置くことだから
- `semgrep` は将来的に security / policy まで広げるなら再評価余地がある

### 5. Repo exploration tooling

| option | purpose | execution surface | failure meaning | introduction cost | notes |
|---|---|---|---|---|---|
| `rg --files`, `rg -n`, `git diff`, `gh issue view`, `scripts/issue_dag.py` | repo / issue / 依存関係の探索を editor 非依存で再現可能にする | review 補助 / issue triage / local preflight | 文脈読み漏れの抑制。CI fail を返す種別ではない | 低 | すでに repo 内の作業流儀と整合 |
| editor / LSP / indexer 依存の探索 | シンボル単位で深い探索を速くする | 開発者ローカル専用 | 結果の再現性が環境依存になりやすい | 中 | 補助用途として有効だが baseline としては固定しにくい |

現状判断:

- repo exploration は「新しい checker 導入」より「使う CLI セットを固定する」方が先
- baseline では `rg` `git` `gh issue view` `scripts/issue_dag.py` を標準セットとして明文化する案が妥当
- CI gate ではなく review 補助として扱う

## 配置案（どこで使うか）

| category | local preflight | CI | review 補助 |
|---|---|---|---|
| `pytest` | yes | yes | yes |
| `ruff check .` | yes | yes | yes |
| `ruff format --check .` | yes | yes | yes |
| `guide-check` | yes | yes (docs 変更時) | yes |
| `mypy` (導入後) | yes | yes | optional |
| `ast-grep` (導入後) | yes | yes | yes |
| `rg` / `git` / `gh issue view` / `issue_dag.py` | optional | no | yes |
| `#208` launch guard | yes | no | no |

要点:

- CI に置くのは「非破壊で、失敗の意味が明確なもの」に寄せる
- repo exploration tooling は fail gate ではなく、読み漏れ削減の deterministic な補助導線として扱う
- launch guard は code quality ではなく side-effect safety として別扱いにする

## 導入順序案

### Phase 0: baseline を明示的に固定する

1. 現在の baseline を `pytest`, `ruff check .`, `ruff format --check .`, `guide-check` として文書化する
2. `review-preflight` / `CODEX_RUNBOOK` で参照する非破壊チェック列をこの baseline に寄せる
3. `#208` を side-effect safety guardrail として並記する

### Phase 1: type checker を 1 つ導入する

1. `mypy` を小さい対象から試す
2. 対象は `src/personal_mcp` 全体一括ではなく、変更頻度の高いモジュールか leaf module から始める
3. 失敗理由が「annotation 不足」なのか「実バグ候補」なのかを分類できる状態を先に作る

### Phase 2: structural constraints を導入する

1. `ast-grep` などで repo 固有の「禁止したい構造」を 2〜3 個に絞って表現する
2. cleanup taxonomy や constitution 整理と混ぜず、純粋に構造制約だけを対象にする
3. 文法チェックや lint では拾えない drift を補う

### Phase 3: repo exploration tooling を runbook 化する

1. `rg --files`, `rg -n`, `git diff --stat`, `gh issue view`, `scripts/issue_dag.py` を review 補助の標準手順として残す
2. CI gate にはせず、deterministic な探索導線として固定する

## Follow-up issue 候補

- type checker 導入 Issue: `mypy` を最小対象で追加し、`make` / CI への置き場を決める
- format check 固定 Issue: `ruff format --check .` を非破壊検査として導入する
- structural constraints Issue: `ast-grep` で repo 固有ルールを 2〜3 個だけ追加する
- exploration runbook Issue: review 補助の標準探索コマンドを文書化する

## 近接 Issue との関係

- `#227`: `make setup`, `make lint`, `make fmt`, `make test` を追加し、現 baseline の入口を作った
- `#208`: 誤 worktree / branch 実行を止める safety guardrail。tool quality check とは別軸
- `#258`: AI 文書の責務整理。ここで扱うのは governance ではなく deterministic toolchain baseline
- `#259`: harness / cleanup architecture の親 Concept。本 Issue はそのうち deterministic toolchain の棚卸しを担う

## 結論

`personal-mcp-core` の deterministic baseline は、現時点では
`pytest` + `ruff check .` + `ruff format --check .` + `guide-check`
を中心に置くのが最も薄くて明快である。

そのうえで、次の追加候補は
`type checker を 1 つ導入する` -> `AST/構造ルールを追加する` -> `repo exploration tooling を標準手順化する`
の順に進める案が、コストと failure surface の説明がしやすい。

## 参照根拠

repo 内:

- `pyproject.toml`: 現在の `ruff` 設定と dev dependencies
- `Makefile`: `setup`, `lint`, `fmt`, `test`, `guide-check`, `issue-dag-list`
- `docs/CODEX_RUNBOOK.md`: `ruff` / `pytest` / safety check の標準フロー
- `docs/CODEX_RUNBOOK.md`: review 前検査と実行フローの固定順序
- `scripts/issue_dag.py`: issue graph 探索の補助スクリプト
- `#208`, `#227`, `#258`, `#259`, `#260`: 近接 Issue と責務境界

外部一次情報:

- Ruff docs: https://docs.astral.sh/ruff/
- Ruff formatter docs: https://docs.astral.sh/ruff/formatter/
- mypy getting started: https://mypy.readthedocs.io/en/stable/getting_started.html
- mypy existing codebase guide: https://mypy.readthedocs.io/en/stable/existing_code.html
- Pyright configuration docs: https://github.com/microsoft/pyright/blob/main/docs/configuration.md
- ast-grep rule reference: https://ast-grep.github.io/reference/rule.html
- Semgrep rule syntax: https://semgrep.dev/docs/writing-rules/rule-syntax
- ripgrep guide: https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md

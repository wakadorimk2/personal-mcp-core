# Cleanup Pipeline — Execution Surfaces and Maintenance Loop

> 種別: execution design / operating model
> Issue: #264
> 親 Issue: #259
> 前提: #260, #261, #262, #263
> 更新日: 2026-03-10
>
> **この文書は cleanup の実行面と記録面を定義する。CI / hook / scheduler の実装導入は後続 Issue へ分離する。**

---

## Goal

`personal-mcp-core` における cleanup を、
「どの signal を入力にするか」
「どの実行面で何を流すか」
「auto-fix / auto-report / manual triage をどこで分けるか」
「Issue / Project にどう記録するか」
の 4 点で repeatable maintenance loop にする。

この文書では、`docs/cleanup-architecture.md` の taxonomy / constitution と、
`docs/doc-drift-detection.md` の detector design を、
実際の運用フローへ接続する。

## Non-goal

- Git hook、CI workflow、cron、scheduler の実装導入
- detector や structural rule 自体の実装完了
- 既存 backlog の一括 cleanup 実行
- cleanup report をその場で自動的に merge / close する運用

## 1. 前提として読む文書

この pipeline は次の 4 つの前提をもとにする。

| 先行 Issue | 文書 / source | この pipeline で使うもの |
|---|---|---|
| `#260` | `Makefile`, `pyproject.toml`, [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) | local preflight / review 補助 / CI 候補の current deterministic baseline |
| `#261` | [`docs/cleanup-architecture.md`](./cleanup-architecture.md) | cleanup taxonomy、automation level、constitution |
| `#262` | [`docs/import-layering-dependency-constraints.md`](./import-layering-dependency-constraints.md) | structural drift の signal と hard fail / advisory 候補 |
| `#263` | [`docs/doc-drift-detection.md`](./doc-drift-detection.md) | doc drift detector の signal、report 形式、triage ルール |

要点:

- `#261` が「cleanup とみなしてよい境界」を固定する
- `#260` の baseline は `pytest`, `ruff check .`, `ruff format --check .`, `guide-check`, repo exploration tooling を指す
- `#260` `#262` `#263` が pipeline に流し込む signal の供給源になる
- 本文書はそれらを「いつ」「どこで」「何として処理するか」に落とす

## 2. Pipeline Inputs

cleanup pipeline が入力として扱う signal は次の 4 群に分ける。

| input family | source | representative signal | primary consumer |
|---|---|---|---|
| task-local observation | 実作業中の diff、近傍 docs / tests、human review | typo、broken link、局所 drift、obsolete 補助記述 | micro cleanup |
| deterministic baseline | `ruff`, `pytest`, `guide-check`, repo exploration tooling | command surface drift、導線不整合、review 前 mismatch | micro cleanup / report |
| structural constraints | import / layering / dependency rule | hard fail 候補、advisory structural drift | report / manual triage |
| doc drift detection | path existence, reference integrity, source-of-truth mismatch, orphan doc drift | stale docs、broken anchor、canonical conflict | report / periodic cleanup |

補足:

- signal の「意味判定」は `#261` の constitution に従う
- detector が signal を返しても、直ちに cleanup 実行とはみなさない
- pipeline は input を `micro cleanup` `periodic cleanup` `doc drift detection` のいずれかへ分類して流す

## 3. Execution Surfaces

cleanup を流す実行面は 4 つに固定する。

| surface | timing | main input | allowed route | expected output | record destination |
|---|---|---|---|---|---|
| task-local loop | 実装 / docs 作業中、または optional local hook | task-local observation、軽量 deterministic check | auto-fix / auto-report | 小さい cleanup patch、または follow-up note 1 件 | 現在の PR、または新規/既存 Issue |
| review preflight | PR 前 review / handoff 前 | deterministic baseline、advisory structural/doc signals | auto-report が基本。bounded auto-fix は別 patch へ委譲 | mismatch list、修正要否の報告 | PR コメント、PR 本文、follow-up Issue |
| CI report | branch / PR 上の非破壊検査 | deterministic baseline、detector report | auto-report のみ | report artifact、failed check、advisory list | CI artifact、PR check summary、follow-up Issue |
| weekly triage | 週次 20 分の棚卸し | CI report、preflight report、orphan inventory、未処理 backlog | manual triage | scope を絞った cleanup Issue / PR plan、dependency 更新 | Issue、Project metadata、運用コメント |

設計意図:

- 即時修正が可能なものは task-local loop へ寄せる
- fix 不能だが観測価値が高いものは review preflight / CI report で止める
- 広域の棚卸しと分割判断は weekly triage に集約する

## 4. Micro Cleanup と Periodic Cleanup の違い

| 観点 | micro cleanup | periodic cleanup |
|---|---|---|
| main trigger | 現在触っている diff の近傍で drift を見つけたとき | report 蓄積、週次棚卸し、repo inventory の見直し時 |
| primary input | 現在の差分、近傍 file、正本 docs、既存テスト | CI/preflight report、orphan 候補、unused path、近接 Issue 群 |
| expected output | 現在の task に同梱できる小さい patch、または follow-up Issue 1 件 | cleanup plan、親子に分割された Issue 群、別 PR に切った cleanup 実行 |
| automation ceiling | `L2` まで | `L3` 前提 |
| turnaround | 同一 task / 同一 PR で回収する | triage 後に別 task として着手する |
| review need | 局所 diff なら短時間 review で足りる | inventory と分割方針の review が先に必要 |

運用ルール:

- micro cleanup は「今の文脈で source of truth が明確」なときだけ current task に同梱する
- periodic cleanup は先に `inventory -> split -> prioritize` を行い、一括修正より分割を優先する

## 5. Routing Rules

pipeline は各 signal を次の 3 ルートへ振り分ける。

### 5.1 Auto-fix

条件:

1. `#261` の auto-fix 条件をすべて満たす
2. category が `micro cleanup`、または `doc drift detection` のうち truth が明確な局所同期である
3. diff が現在の task か、その隣接 patch として閉じる

典型例:

- typo / broken link 修正
- README や runbook を canonical doc に同期
- 正本が明確な command surface drift の補正

出力:

- 現在の branch 上の小さい patch
- 必要なら PR 本文に `trigger / source of truth / decision / scope / automation level / evidence` を明記

### 5.2 Auto-report

条件:

- signal は deterministic に観測できる
- ただし apply は unsafe、または scope が current task を超える

典型例:

- doc drift detector が返す mismatch list
- advisory structural rule 違反候補
- command surface drift のうち、docs と実装のどちらが truth か未確定なもの

出力:

- report artifact
- PR comment / check summary
- follow-up Issue draft の材料

原則:

- auto-report は「修正しない」のではなく、「triage 入力を lossless に残す」ためのルートとする
- detector が `false positive` の可能性を含む場合も evidence は残す

### 5.3 Manual triage

条件:

- category が `periodic cleanup`
- canonical が未確定
- structural / contract / responsibility change に波及する
- diff が広く、inventory と分割なしでは監査不能

典型例:

- orphan doc 候補の棚卸し
- docs / policy / runbook の責務重複の見直し
- structural drift を hard fail に上げる前の例外整理

出力:

- scope を絞った cleanup parent Issue
- child Issue への分割
- `blocked-by` / `sub-issue` の dependency 整理

## 6. End-to-End Flow

cleanup pipeline の標準フローは次の順序に固定する。

1. `detect`
   - task-local observation、detector、baseline check から signal を得る
2. `classify`
   - `micro cleanup` / `periodic cleanup` / `doc drift detection`
   - automation level (`L0-L3`)
   - source of truth の明確さ
3. `route`
   - auto-fix / auto-report / manual triage のいずれかに振り分ける
4. `execute`
   - task-local patch、report 出力、または triage issue 化を行う
5. `record`
   - Issue / PR / Project に判断理由と残件を残す

```text
signal
  -> classify(category, automation, truth)
  -> route(auto-fix | auto-report | manual triage)
  -> execute(surface-specific action)
  -> record(issue/pr/project evidence)
```

重要:

- route 前に fix しない
- record を省略して「気づいた人の記憶」に戻さない
- periodic cleanup は execute の前に split を挟んでよい

## 7. Record Destinations

cleanup の記録先は「何を実行したか」ではなく、
「なぜその route にしたか」が読める形にそろえる。

### 7.1 PR に残すもの

現在の task に同梱した micro cleanup は、PR 説明またはレビューコメントに次を残す。

- trigger
- category
- source of truth
- decision
- scope
- automation level
- evidence

これは `docs/cleanup-architecture.md` の Required Evidence を、そのまま PR 面に写す運用である。

### 7.2 Issue に残すもの

current task で回収しないものは follow-up Issue に切り出す。

使い分け:

- micro cleanup だが current scope を超える: 単独 follow-up Issue 1 件
- periodic cleanup: parent Issue を作り、child Issue に分割
- detector-only signal: report を evidence にして triage 用 Issue へ接続

Issue 本文には少なくとも次を含める。

- trigger / category / source of truth / decision / scope / automation level / evidence
- 必要なら `blocked by #...`
- parent がある場合は `sub-issue of #...`

### 7.3 Project に残すもの

Project は backlog の倉庫ではなく active management 面として使う。
したがって cleanup 系 Issue の Project 反映は次で分ける。

- report-only / backlog 段階: 基本は Project に載せない
- weekly triage で着手候補になった periodic cleanup: Project に追加して `Status` を更新する
- active child を持つ parent cleanup issue: Epic として必要な間だけ残す
- `Priority` は active/ready の cleanup issue に限って付ける

dependency の扱い:

- 実行順序を持つ分割は `sub-issue`
- 直接 blocker がある場合だけ `blocked-by`
- 文脈参照だけなら `refs`

## 8. Recommended Operating Cadence

実行 cadence は次を最小セットとする。

| cadence | action | outcome |
|---|---|---|
| 毎 task | task-local loop で micro cleanup を即回収する | 局所 drift を backlog 化しすぎない |
| 毎 review / handoff | review preflight で report を残す | safe fix 不能な signal を落とさない |
| 毎 PR / branch check | CI report で機械観測結果を残す | 手元差以外の drift を継続可視化する |
| 毎週 20 分 | weekly triage で report を整理し、Issue / Project に反映する | periodic cleanup を分割して active 管理へ接続する |

## 9. Summary

cleanup pipeline は、
micro cleanup を「その場で bounded に回収する loop」へ、
periodic cleanup を「report を蓄積して triage で分割する loop」へ分ける。

この文書で固定したのは次の 4 点である。

- 入力は task-local observation / deterministic baseline / structural constraints / doc drift detection の 4 群に分ける
- 実行面は task-local loop / review preflight / CI report / weekly triage の 4 面に固定する
- route は auto-fix / auto-report / manual triage の 3 種に分ける
- 記録先は PR / Issue / Project を使い分け、cleanup evidence と dependency を残す

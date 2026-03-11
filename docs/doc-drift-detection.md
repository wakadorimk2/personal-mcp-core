# Doc Drift Detection — Signals, Detectors, and Triage

> 種別: 方針整理 / detector design
> Issue: #263
> 親 Issue: #259
> 関連: #258, #261
> 更新日: 2026-03-10
>
> **この文書は detector の設計を扱う。実装導入、CI 組み込み、自動修正パイプラインは後続 Issue へ分離する。**

---

## Goal

doc drift / stale docs を
「どの signal に分けて観測するか」
「各 signal を何で deterministic に検知するか」
「検知結果をどう triage するか」
の 3 点で固定する。

この文書では、`docs/cleanup-architecture.md` で定義した
`doc drift detection` category の詳細化を扱う。

補足:

- 2026-03-10 時点で `#261` は closed であり、cleanup taxonomy / constitution は
  [`docs/cleanup-architecture.md`](./cleanup-architecture.md) を正本として参照できる
- `#258` は AI docs / policy の source-of-truth 整理であり、
  canonical が未固定な領域では detector は report-only を原則とする

## Non-goal

- detector の実装完了
- docs inventory の全面自動生成
- stale docs を一括削除する cleanup の実行
- source of truth が未確定な領域の意味判断をこの文書だけで固定すること

## 1. Detection Principles

doc drift detector は次の原則で設計する。

1. signal は意味論より先に、機械的に観測できる差分へ分解する
2. detector はまず local で安く回せるものを優先する
3. 検知結果は即 auto-fix せず、cleanup / spec change / false positive に分類する
4. source of truth が曖昧な領域では hard fail ではなく advisory に留める
5. detector 自体が repo 運用を壊さないよう、初期段階は `L0 detect only` を基本とする

## 2. Signal Taxonomy

| signal | 何を検知するか | 代表例 | 初期 automation |
|---|---|---|---|
| path existence drift | 参照している file / dir / script / doc path が存在しない | `docs/...` へのリンク先が削除済み | `L0` |
| reference integrity drift | Markdown link, anchor, doc-to-doc 参照が解決しない | `#section` anchor 不一致、相対リンク broken | `L0` |
| source-of-truth mismatch | 同じ topic に複数の canonical 宣言や矛盾がある | 「正本」が 2 つある、導線が別の正本を指す | `L0` |
| command surface drift | runbook / README のコマンドや target が実在しない | `make` target 名、CLI subcommand 名が古い | `L0` |
| orphan doc drift | 参照導線を失った docs が残留している | README や index から到達不能な issue doc | `L0` |

注記:

- `path existence drift` と `reference integrity drift` は似ているが分ける
- 前者は「参照対象の実体があるか」、後者は「リンクの解決規則まで含めて成立するか」
- `source-of-truth mismatch` は `#258` と強く接続し、cleanup より spec change に流れる可能性が高い

## 3. Detector Candidates by Signal

### 3.1 Path Existence Drift

対象:

- Markdown の相対パスリンク
- docs 内で明示された `docs/...`, `scripts/...`, `src/...` 参照
- runbook や policy で名前付きで言及されたファイルパス

detector 候補:

| candidate | 方法 | local cost | notes |
|---|---|---|---|
| markdown path resolver | `*.md` の相対リンクを抽出し、repo root 基準で存在確認する | 低 | 初手で最も導入しやすい |
| literal path grep check | `docs/`, `scripts/`, `src/` を含む literal path を抽出し、`git ls-files` と照合する | 低 | link 記法でない参照にも効く |
| allowlist-aware path scan | archive / generated file など例外 path を allowlist 化して除外する | 低〜中 | false positive 抑制用 |

低コスト local 候補:

- `rg -n '\]\((\./|\.\./)[^)]+\.md([)#][^)]*)?\)' README.md docs AI_GUIDE.md CLAUDE.md`
- `git ls-files`

### 3.2 Reference Integrity Drift

対象:

- Markdown anchor link
- doc 間の section 参照
- README や runbook からの intra-doc 導線

detector 候補:

| candidate | 方法 | local cost | notes |
|---|---|---|---|
| heading-anchor checker | 見出しから anchor を正規化生成し、`#...` リンクが解決するか検査する | 低 | path existence では拾えない broken anchor を取れる |
| markdown graph validator | file node + anchor node の graph を作り、未解決参照を列挙する | 中 | orphan 判定の基礎にも使える |
| duplicate heading detector | 同一 file 内の重複見出しで anchor が衝突していないか見る | 低 | false positive は少ない |

低コスト local 候補:

- `rg -n '\]\([^)]*#.*\)' README.md docs AI_GUIDE.md CLAUDE.md`
- 見出し抽出だけを行う軽量 script

### 3.3 Source-of-Truth Mismatch

対象:

- `正本`, `source of truth`, `canonical`, `唯一` などの canonical 宣言
- 同一 topic に対する責務境界の矛盾
- 導線文書が別の正本を指しているケース

detector 候補:

| candidate | 方法 | local cost | notes |
|---|---|---|---|
| canonical-claim inventory | canonical 宣言を grep 収集し、topic ごとに一覧化する | 低 | `#258` との接続点 |
| topic-to-source matrix | topic ごとに canonical file を 1 つ割り当て、複数宣言を mismatch とする | 中 | topic map の初期定義が必要 |
| downstream-sync check | 導線 docs が canonical file を参照しているか確認する | 低〜中 | canonical が固定済みの topic に限定する |

低コスト local 候補:

- `rg -n '正本|source of truth|canonical|唯一' README.md AI_GUIDE.md CLAUDE.md docs`

triage 上の扱い:

- canonical が 1 つに定まらない場合は cleanup ではなく spec change 候補
- 特に AI docs / policy 領域は `#258` の責務整理と衝突しうるため、初期運用は advisory 固定とする

### 3.4 Command Surface Drift

対象:

- `make` targets
- CLI subcommands / flags
- runbook に書かれた実行順序や command surface

detector 候補:

| candidate | 方法 | local cost | notes |
|---|---|---|---|
| make target existence check | docs で言及された `make <target>` を抽出し、`Makefile` 定義と照合する | 低 | README / runbook に効く |
| CLI surface snapshot check | docs で言及された subcommand / flag を `--help` 出力と照合する | 中 | 実装を truth 側に寄せる検査 |
| script path + executable check | `scripts/...` の存在と実行属性を確認する | 低 | runbook stale 検知の初手 |

低コスト local 候補:

- ``rg -n '`make [^`]+`|make [A-Za-z0-9_-]+' README.md docs``
- `rg -n 'python -m personal_mcp\\.server [A-Za-z0-9_-]+' README.md docs`

### 3.5 Orphan Doc Drift

対象:

- repo 内にあるが、主要導線から参照されない docs
- 役目を終えた issue-specific docs
- どこにもリンクされず保守責任が曖昧な文書

detector 候補:

| candidate | 方法 | local cost | notes |
|---|---|---|---|
| reverse-link graph | `*.md` 間のリンク graph を作り、root から到達不能な file を列挙する | 中 | 最も明快な orphan detector |
| root-set policy | `README.md` と topic index を root とし、そこから未到達の docs を advisory として出す | 低〜中 | docs 構造が小さい間は十分 |
| explicit-retention allowlist | issue 証跡として残す docs を allowlist 化する | 低 | false positive を deterministic に消せる |

低コスト local 候補:

- `rg --files -g '*.md'`
- Markdown link graph を作る軽量 script

注意:

- orphan は即 garbage ではない
- 証跡 docs や将来参照前提の design memo は、retention policy があれば orphan 扱いしない

## 4. Reporting Surface

detector は最初から fail-fast にせず、まずは mismatch report を返す。

最小 report 形式:

| field | meaning |
|---|---|
| signal | どの signal で検出したか |
| subject | 対象 file / command / topic |
| evidence | 未解決 path、broken anchor、canonical claim などの生 evidence |
| source | 検出元 file |
| candidate truth | 同期先候補、または「未確定」 |
| suggested triage | cleanup / spec change / false positive |
| confidence | high / medium / low |

運用面:

- local 実行では Markdown table または JSON lines のどちらかで出せればよい
- CI 導入前の段階では、まず `artifacts` や PR comment に貼れる形を優先する
- 1 回の report で auto-fix まで進めず、triage 後に別 action を起こす

## 5. Triage Rules

`docs/cleanup-architecture.md` の constitution に従い、検知結果は次の順で処理する。

1. signal を確定する
2. canonical が明確かを確認する
3. cleanup / spec change / false positive に分類する
4. cleanup だけを follow-up patch 候補に残す

分類ルール:

| case | triage | reason |
|---|---|---|
| path, anchor, command が単純に壊れており truth が明確 | cleanup | 既存正本への同期で説明できる |
| canonical claim が衝突している | spec change | どちらに合わせるかが新規判断になる |
| orphan に見えるが retention 理由がある | false positive | 削除根拠が不足している |
| 実装と docs のどちらが正しいか決められない | spec change | detector 単体では fix 不能 |
| 同じ signal が継続発生し、例外として定着している | false positive ではなく rule gap | allowlist か detector 改修を検討する |

## 6. False Positive Handling

false positive を黙殺せず、次のいずれかで deterministic に処理する。

1. allowlist に追加する
2. retention reason を doc 自体に書く
3. detector の対象 root / pattern を狭める

やってはいけないこと:

- 「たぶん必要」で orphan 判定を解除する
- canonical 不明のまま cleanup patch を出す
- 例外理由を Issue コメントだけに閉じ込める

## 7. Relationship with #261 and #258

### With `#261`

- `#261` は cleanup taxonomy / constitution を固定した
- この文書はその中の `doc drift detection` category に detector の粒度を与える
- automation ceiling は引き続き detect `L0` を基本とし、apply は別 triage 後にのみ扱う

### With `#258`

- `#258` は AI docs / policy の source-of-truth 整理であり、
  detector の `source-of-truth mismatch` signal と直接つながる
- `#258` で canonical mapping が固定されるまでは、
  当該領域の mismatch は cleanup ではなく spec change 候補として報告する
- 逆に `#258` 完了後は、その mapping を detector 入力に流用できる

## 8. Initial Rollout Order

低コスト順に次を推奨する。

1. path existence drift
2. reference integrity drift
3. command surface drift
4. source-of-truth mismatch
5. orphan doc drift

理由:

- 最初の 3 つは false positive が比較的少なく、local 実行コストも低い
- `source-of-truth mismatch` は `#258` に依存しやすい
- orphan 判定は link graph と retention policy が必要で、導入初期は advisory に留めるのが安全

## 9. Summary

doc drift / stale docs は 1 種類の問題ではなく、少なくとも
`path existence`, `reference integrity`, `source-of-truth mismatch`,
`command surface drift`, `orphan doc drift`
に分けて扱うのが妥当である。

各 signal には local で回せる deterministic detector 候補があり、
初期運用では `L0 detect only` を基本として
report -> triage -> follow-up cleanup/spec change
の順に流す。

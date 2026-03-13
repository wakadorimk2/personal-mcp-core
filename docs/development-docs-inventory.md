# Development Docs Inventory and Canonical Ownership Map

> Issue: #416
> Parent epic: #415
> Purpose: docs 再編前の inventory / ownership / overlap 候補を 1 か所に集約する
> Status: draft inventory baseline
> Updated: 2026-03-14

## 1. Scope

この文書は、`docs/` 配下の開発運用文書を棚卸しし、
後続 Issue が同じ前提で統合判断できるようにするための inventory である。

この Issue では次を扱う。

- `docs/**/*.md` の現状 inventory
- concern ごとの canonical ownership proposal
- 重複の強い文書群と統合候補の識別
- `retain / integrate / stub / retire candidate` の一次提案

この Issue では次を扱わない。

- 大規模な文書移動や削除
- source of truth 自体の再定義
- protocol / contract の仕様変更
- index / stub 導線の本実装

## 2. Inventory Boundary

### 2.1 In scope

主 inventory の対象は `docs/**/*.md` の 56 ファイルとする。

| group | count | note |
|---|---:|---|
| `docs/` top-level | 39 | policy, runbook, spec, architecture, issue-specific docs を含む |
| `docs/skills/` | 12 | canonical skill docs |
| `docs/infra/` | 5 | infra / notification / backup 関連 docs |

inventory の最小単位は「1 file = 1 row」とする。

### 2.2 Comparison-only files

次の文書は `docs/` 外だが、導線や重複判定に影響するため比較対象として扱う。

| path | reason |
|---|---|
| `AGENTS.md` | repo-wide entrypoint と read order の基準 |
| `AI_GUIDE.md` | AI behavior / priming の導線と source-of-truth 参照 |
| `CLAUDE.md` | runtime-specific guidance の比較対象 |
| `src/personal_mcp/AI_GUIDE.md` | guide copy の同期有無を確認するための補助対象 |
| `.codex/skills/*/SKILL.md` | canonical skill doc からの adapter 層比較 |
| `.claude/skills/*/SKILL.md` | canonical skill doc からの adapter 層比較 |

比較対象は inventory table の主行には含めず、
canonical ownership と overlap 判断の補助 evidence としてのみ参照する。

### 2.3 Out of scope for this inventory

次の文書は repo に存在していても、今回の主 inventory から除外する。

| path | reason |
|---|---|
| `README.md` | repo 全体の利用案内であり、今回の「開発運用 docs」主対象から外す |
| `data/README.md` | data directory の補助説明であり、開発運用 docs inventory の本体ではない |
| `.github/PULL_REQUEST_TEMPLATE.md` | GitHub template であり、docs IA 再編の直接対象ではない |
| `.pytest_cache/README.md` | tool-generated file |

## 3. Inventory Columns

各 file は次の列で整理する。

| column | meaning |
|---|---|
| `path` | 文書の path |
| `title` | 先頭見出しの title |
| `primary purpose` | その文書が主に何を説明・固定・記録しているか |
| `audience` | `human` / `AI` / `both` |
| `category` | `architecture` / `runbook` / `tooling` / `spec` / `index` / `skill` |
| `canonical status` | `canonical` / `reference` / `record` |
| `overlap cluster` | 重複や近接がある文書群ラベル |
| `proposed action` | `retain` / `integrate` / `stub` / `retire candidate` |
| `notes` | 判定理由、後続 Issue への申し送り、比較対象との関係 |

補足:

- `canonical` は concern の primary source を意味する
- `reference` は導線・補助説明・運用補助を意味する
- `record` は issue-specific note、snapshot、research memo、decision log などの証跡寄り文書を意味する

## 4. Evaluation Rules

判定は次の順で行う。

1. file ごとの主目的を短く固定する
2. その目的に対して主読者を `human / AI / both` で置く
3. category を 1 つ選ぶ
4. canonical status を `canonical / reference / record` で置く
5. overlap cluster を付与する
6. `retain / integrate / stub / retire candidate` を提案する

`record` 判定の文書は、すぐに retire 候補とみなさない。
issue evidence として残す合理性がある場合は `retain` になりうる。

## 5. Exit Criteria for #416

この文書が `#416` の成果物として機能するための最低条件は次のとおり。

- `docs/**/*.md` 56 件が inventory されている
- concern ごとの canonical ownership proposal がある
- overlap cluster が明示されている
- `retain / integrate / stub / retire candidate` の一次提案がある
- `#417`, `#418`, `#419` が参照すべき範囲が区別されている

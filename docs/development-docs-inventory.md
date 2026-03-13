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

## 6. Inventory Table

### 6.1 Top-level docs

| path | title | primary purpose | audience | category | canonical status | overlap cluster | proposed action | notes |
|---|---|---|---|---|---|---|---|---|
| `docs/AI_ROLE_POLICY.md` | AI Role Boundary Policy（共通） | runtime role boundary と side-effect policy を固定する | both | architecture | canonical | `ai-system-core` | integrate | `#417` の主要入力 |
| `docs/AI_WORKFLOW.md` | AI Workflow (Git / worktree / VSCode) | worktree / branch / VSCode 運用の正本を置く | both | runbook | canonical | `ai-system-core` | integrate | `PLAYBOOK` と近接 |
| `docs/CODEX_RUNBOOK.md` | CODEX_RUNBOOK | Codex runtime の実行順序と停止条件を定義する | AI | runbook | canonical | `ai-runbook-skill` | integrate | `PLAYBOOK` と skills への重複がある |
| `docs/PLAYBOOK.md` | AI Worker Playbook | worker 共通の intake から handoff までの流れを定義する | both | runbook | canonical | `ai-system-core` | integrate | workflow と runbook の中間にある |
| `docs/RUNBOOK_BASELINE.md` | Runtime-Specific Runbook Baseline | runtime-specific runbook の基準構造を定義する | both | spec | canonical | `ai-runbook-skill` | retain | meta-level baseline |
| `docs/WORKER_POLICY.md` | AI Worker Policy | task-class ごとの dispatch policy を定義する | both | architecture | canonical | `ai-system-core` | integrate | role / workflow / claim docs と近接 |
| `docs/adapters.md` | Adapters | adapter 層と外部 input surface の補助説明を置く | both | architecture | reference | `core-architecture` | retain | `architecture.md` の補助 |
| `docs/ai-notification-contract-v1.md` | AI Notification Contract v1 | AI 通知 payload と field contract を固定する | both | spec | canonical | `notification-infra` | retain | notify wrapper 群の上位契約 |
| `docs/architecture.md` | Architecture | システム構造と layer responsibilities を説明する | both | architecture | canonical | `core-architecture` | retain | repo の core structure 正本 |
| `docs/candidate-api-v1.md` | candidate API v1 | `GET /api/candidates` の最小 API 契約を固定する | both | spec | canonical | `daily-input` | retain | daily input contract 群 |
| `docs/cleanup-architecture.md` | Cleanup Architecture — Taxonomy and Constitution | cleanup taxonomy / constitution を定義する | both | architecture | canonical | `cleanup` | retain | cleanup 系の親文書 |
| `docs/cleanup-pipeline.md` | Cleanup Pipeline — Execution Surfaces and Maintenance Loop | cleanup の実行面と maintenance loop を定義する | both | runbook | canonical | `cleanup` | retain | cleanup architecture の実行面 |
| `docs/daily-input-mode-contract-v1.md` | daily input mode contract v1 | quick / tag / text の mode 責務を固定する | both | spec | canonical | `daily-input` | retain | UX 比較の契約 |
| `docs/daily-input-ux-mvp.md` | daily input UX — MVP 方針定義 | daily input UI の north star を記録する | both | architecture | canonical | `daily-input` | retain | UI 方針の親文書 |
| `docs/data-directory.md` | repo 内 `data/` の位置づけと運用ルール | repo 内外の data-dir 運用境界を説明する | both | runbook | canonical | `storage-recovery` | retain | restore / migration と近接 |
| `docs/design-principles.md` | Design Principles — Architecture North Star | 設計思想と north star を明文化する | both | architecture | canonical | `core-architecture` | retain | architecture の上位思想 |
| `docs/deterministic-toolchain-baseline.md` | Deterministic Toolchain Baseline — Issue #260 | local / CI の deterministic toolchain 前提を固定する | both | tooling | canonical | `cleanup` | retain | review / cleanup の基準 |
| `docs/doc-drift-detection.md` | Doc Drift Detection — Signals, Detectors, and Triage | doc drift detector の signal と triage を定義する | both | tooling | canonical | `cleanup` | retain | cleanup pipeline の入力 |
| `docs/domain-extension-policy.md` | domain 拡張ポリシー | domain 追加時の gate を固定する | both | architecture | canonical | `event-contract` | retain | domain contract 群の入口 |
| `docs/eng-domain-concept.md` | eng domain concept / contract | `eng` domain の concept / contract を置く | both | spec | canonical | `eng-ingest` | retain | eng 系の domain contract |
| `docs/eng-ingest-impl.md` | eng domain GitHub Ingest — 実装責務定義 (#204) | GitHub ingest の responsibility split を記録する | both | architecture | reference | `eng-ingest` | retain | contract というより impl note |
| `docs/event-contract-v1.md` | Event Contract v1 | event record の canonical contract を定義する | both | spec | canonical | `event-contract` | retain | repo 全体の主要 contract |
| `docs/git-branch-cleanup-cheatsheet.md` | Git branch 整理チートシート | branch cleanup の実用コマンドをまとめる | both | runbook | reference | `ai-runbook-skill` | integrate | 日常運用 runbook へ寄せやすい |
| `docs/heatmap-density-audit-2026-03-12.md` | Heatmap Density Audit Snapshot (2026-03-12) | heatmap density 実測 snapshot を残す | human | tooling | record | `heatmap` | retain | issue evidence として読む文書 |
| `docs/heatmap-density-audit.md` | Heatmap Density Audit | density audit の方針と command surface を定義する | both | tooling | canonical | `heatmap` | retain | snapshot と対になる |
| `docs/heatmap-state-density-spec.md` | Heatmap v1 Density Semantics — Decision Record | heatmap density semantics の決定事項を固定する | both | spec | canonical | `heatmap` | retain | heatmap v1 の上位決定 |
| `docs/import-layering-dependency-constraints.md` | Import / Layering / Dependency Constraints — Issue #262 | import / layering 制約を定義する | both | architecture | canonical | `core-architecture` | retain | architecture の制約面 |
| `docs/issue-213-daily-log-input-frictions.md` | Issue #213: 日常ログ入力の操作摩擦メモ | UX 改善の issue-specific memo を残す | human | architecture | record | `daily-input` | retire candidate | canonical doc へ内容吸収済みの可能性が高い |
| `docs/issue-79-proposal-review.md` | Issue #79 Proposal Review | old event contract proposal の review memo を残す | human | spec | record | `event-contract` | retire candidate | `event-contract-v1` で代替されている |
| `docs/kind-taxonomy-v1.md` | Kind Taxonomy v1 | Event Contract v1 の kind taxonomy を定義する | both | spec | canonical | `event-contract` | retain | contract 補助の正本 |
| `docs/migration.md` | コマンド移行方針 | legacy command / path 移行方針を記録する | both | runbook | reference | `storage-recovery` | integrate | `data-directory` と storage plan に近接 |
| `docs/mvp-contract-decisions.md` | MVP Contract Decisions — Annotation / Interpretation / Summary 責務境界 | MVP decision record を固定する | both | spec | canonical | `event-contract` | retain | decision record として読む |
| `docs/post-candidate-contract-v1.md` | 短文投稿候補 Contract v1 | post candidate 生成の最小 contract を定義する | both | spec | canonical | `post-candidate` | retain | post-candidate skill の入力契約 |
| `docs/storage-unification-plan.md` | Storage Unification Plan (#185) | storage unification の decision / migration record を残す | both | spec | record | `storage-recovery` | retain | 履歴と現状メモが混在する |
| `docs/unified-input-ui-187.md` | 統合入力UI方針（Issue #187） | unified input UI の issue-specific 方針を置く | both | architecture | reference | `daily-input` | integrate | 既に `daily-input-ux-mvp` を参照している |
| `docs/usage-monitor-research.md` | Usage Monitor Research — Issue #120 | usage monitor の調査結果と提案を残す | human | tooling | record | `usage-research` | retain | research memo として独立 |
| `docs/worker-claim-protocol.md` | worker claim protocol v1 | claim / release / handoff event log を定義する | both | spec | canonical | `worker-coordination` | retain | worker coordination の protocol |
| `docs/worker-domain.md` | worker domain contract | worker event / state の domain contract を定義する | both | spec | canonical | `worker-coordination` | retain | worker 系の domain contract |
| `docs/worker-registry-coordination.md` | worker registry coordination boundary | GitHub と registry の canonical source 境界を定義する | both | spec | canonical | `worker-coordination` | retain | claim protocol と一体で参照される |

### 6.2 Infra docs

| path | title | primary purpose | audience | category | canonical status | overlap cluster | proposed action | notes |
|---|---|---|---|---|---|---|---|---|
| `docs/infra/ai-cli-discord-smoke-log.md` | AI CLI Discord smoke log | Discord webhook 実送信確認の log を残す | human | tooling | record | `notification-infra` | retire candidate | log 性格が強く常設 docs には重い |
| `docs/infra/backup-mvp-options.md` | MVPバックアップ戦略の比較表 | MVP backup 方針の比較材料を整理する | human | architecture | reference | `storage-recovery` | retain | restore draft の前提比較表 |
| `docs/infra/discord-webhook-channel-contract.md` | Discord webhook channel contract | Discord adapter の最小 contract を定義する | both | spec | canonical | `notification-infra` | retain | notify wrapper の channel contract |
| `docs/infra/notify-wrapper.md` | notify wrapper | `scripts/notify` wrapper の interface と metadata を説明する | both | tooling | canonical | `notification-infra` | retain | ai-notification contract と近接 |
| `docs/infra/restore-mvp-draft.md` | バックアップからの復元手順（MVPドラフト） | backup からの復元手順ドラフトを置く | human | runbook | reference | `storage-recovery` | integrate | `draft` 状態で data-dir docs と近接 |

### 6.3 Skill docs

| path | title | primary purpose | audience | category | canonical status | overlap cluster | proposed action | notes |
|---|---|---|---|---|---|---|---|---|
| `docs/skills/clarify-request.md` | clarify-request | request を Goal / Scope / AC / Constraints に整理する skill を定義する | AI | skill | canonical | `skill-intake` | retain | 高頻度だが独立責務が明確 |
| `docs/skills/codex-claude-bridge.md` | codex-claude-bridge | Codex から Claude への handoff prompt を生成する skill を定義する | AI | skill | canonical | `skill-handoff` | retain | bridge 専用で独立性が高い |
| `docs/skills/implement-only.md` | implement-only | Claude proposal-only 実装提案 skill を定義する | AI | skill | canonical | `skill-impl` | retain | `minimal-safe-impl` と境界で読む |
| `docs/skills/issue-create.md` | issue-create | `gh issue create` 手順を標準化する skill を定義する | AI | skill | canonical | `skill-github-ops` | integrate | 日常 GitHub ops と強く近接 |
| `docs/skills/issue-draft.md` | issue-draft | structured issue body を生成する skill を定義する | AI | skill | canonical | `skill-intake` | retain | create 前の固有工程 |
| `docs/skills/issue-project-meta.md` | issue-project-meta | Projects metadata 更新手順を標準化する skill を定義する | AI | skill | canonical | `skill-github-ops` | integrate | GitHub ops runbook に寄せやすい |
| `docs/skills/issue-split.md` | issue-split | large issue を DAG 付き child issue に分割する skill を定義する | AI | skill | canonical | `skill-intake` | retain | specialized workflow |
| `docs/skills/minimal-safe-impl.md` | minimal-safe-impl | issue 実装を最小差分で進める skill を定義する | AI | skill | canonical | `skill-execution` | integrate | runbook と重複する実行順序がある |
| `docs/skills/post-candidate.md` | post-candidate | daily logs から短文投稿候補を作る skill を定義する | AI | skill | canonical | `skill-specialized` | retain | specialized domain skill |
| `docs/skills/research-propose-structured.md` | research-propose-structured | 調査結果を構造化結論で返す skill を定義する | AI | skill | canonical | `skill-intake` | retain | research 専用の出力契約 |
| `docs/skills/review-diff.md` | review-diff | diff review の findings-first 出力を定義する | AI | skill | canonical | `skill-review` | integrate | review runbook と近接 |
| `docs/skills/review-preflight.md` | review-preflight | merge 前の preflight check と報告形式を定義する | AI | skill | canonical | `skill-review` | integrate | runbook と重複する検査順序がある |

## 7. Overlap Clusters

inventory 上の overlap cluster は、統合判断の単位として次の意味で使う。

| cluster | included docs | why grouped | likely owner issue |
|---|---|---|---|
| `ai-system-core` | `AI_ROLE_POLICY`, `AI_WORKFLOW`, `PLAYBOOK`, `WORKER_POLICY` | AI priming / role / workflow / dispatch の境界が近い | `#417` |
| `ai-runbook-skill` | `RUNBOOK_BASELINE`, `CODEX_RUNBOOK`, `git-branch-cleanup-cheatsheet` | 日常実行手順と runtime-specific runbook が近い | `#418` |
| `worker-coordination` | `worker-claim-protocol`, `worker-domain`, `worker-registry-coordination` | worker claim / state / registry の protocol 群 | `#417` |
| `core-architecture` | `design-principles`, `architecture`, `adapters`, `import-layering-dependency-constraints` | repo の構造・思想・制約を扱う | follow-up only |
| `cleanup` | `cleanup-architecture`, `cleanup-pipeline`, `doc-drift-detection`, `deterministic-toolchain-baseline` | cleanup / maintenance system の設計群 | retain |
| `event-contract` | `event-contract-v1`, `kind-taxonomy-v1`, `domain-extension-policy`, `mvp-contract-decisions`, `issue-79-proposal-review` | event / domain / kind / summary の契約群 | retain |
| `storage-recovery` | `data-directory`, `migration`, `storage-unification-plan`, `backup-mvp-options`, `restore-mvp-draft` | data-dir, migration, backup, restore が近い | follow-up only |
| `daily-input` | `daily-input-ux-mvp`, `daily-input-mode-contract-v1`, `candidate-api-v1`, `unified-input-ui-187`, `issue-213-daily-log-input-frictions` | daily input UX / API / issue memo 群 | follow-up only |
| `heatmap` | `heatmap-state-density-spec`, `heatmap-density-audit`, `heatmap-density-audit-2026-03-12` | heatmap semantics と audit 方針 / snapshot | retain |
| `eng-ingest` | `eng-domain-concept`, `eng-ingest-impl` | `eng` domain contract と ingest 実装メモ | retain |
| `notification-infra` | `ai-notification-contract-v1`, `infra/notify-wrapper`, `infra/discord-webhook-channel-contract`, `infra/ai-cli-discord-smoke-log` | 通知 payload / wrapper / adapter / log 群 | follow-up only |
| `skill-intake` | `clarify-request`, `issue-draft`, `issue-split`, `research-propose-structured` | issue 前段・調査系 skill 群 | `#418` |
| `skill-review` | `review-diff`, `review-preflight` | review / preflight 手順が runbook と近い | `#418` |
| `skill-execution` | `minimal-safe-impl`, `implement-only` | 実装実行と proposal-only の境界で読む skill 群 | `#418` |
| `skill-github-ops` | `issue-create`, `issue-project-meta` | GitHub 操作手順をまとめた skill 群 | `#418` |

補足:

- `AGENTS.md`, `AI_GUIDE.md`, `CLAUDE.md`, `.codex/.claude` adapter 群は主 inventory 行には含めないが、`ai-system-core` と `skill-*` cluster の比較対象として読む
- `follow-up only` は `#417/#418/#419` の主対象ではなく、必要なら別 issue に切り出す方が安全な群を意味する

## 8. Canonical Ownership Map

### 8.1 Concern-to-source map

| concern | current canonical source | main downstream / nearby docs | note |
|---|---|---|---|
| repo entrypoint and read order | `AGENTS.md` | `AI_GUIDE.md`, runtime runbooks | `docs/` 外の routing source |
| AI behavior principles | `AI_GUIDE.md` | `AGENTS.md`, `CLAUDE.md`, `architecture.md` | comparison-only だが priming 上は重要 |
| runtime role boundary | `docs/AI_ROLE_POLICY.md` | `AI_GUIDE.md`, `CLAUDE.md`, `CODEX_RUNBOOK.md` | `#417` の統合対象 |
| worktree / branch / VSCode workflow | `docs/AI_WORKFLOW.md` | `PLAYBOOK.md`, `git-branch-cleanup-cheatsheet.md` | `#417` と `#418` の境界面 |
| worker common lifecycle | `docs/PLAYBOOK.md` | `AI_WORKFLOW.md`, `CODEX_RUNBOOK.md` | `#417` と `#418` の接続点 |
| dispatch policy | `docs/WORKER_POLICY.md` | `AI_ROLE_POLICY.md`, `PLAYBOOK.md` | `#417` の統合対象 |
| runtime-specific runbook baseline | `docs/RUNBOOK_BASELINE.md` | `CODEX_RUNBOOK.md` | retain 候補 |
| Codex runtime execution steps | `docs/CODEX_RUNBOOK.md` | `PLAYBOOK.md`, `minimal-safe-impl`, `review-preflight` | `#418` の統合対象 |
| worker claim / handoff protocol | `docs/worker-claim-protocol.md` | `PLAYBOOK.md`, `WORKER_POLICY.md` | protocol child doc として retain 寄り |
| registry coordination boundary | `docs/worker-registry-coordination.md` | `worker-claim-protocol.md`, `WORKER_POLICY.md` | protocol child doc として retain 寄り |
| worker event / state contract | `docs/worker-domain.md` | worker tooling and registry docs | protocol child doc として retain 寄り |
| core system structure | `docs/architecture.md` | `adapters.md`, `design-principles.md` | AI docs 統合とは切り分けたい |
| design north star | `docs/design-principles.md` | `architecture.md`, contract docs | retain |
| event record contract | `docs/event-contract-v1.md` | `kind-taxonomy-v1.md`, `domain-extension-policy.md` | retain |
| kind taxonomy | `docs/kind-taxonomy-v1.md` | `event-contract-v1.md` | retain |
| domain gate policy | `docs/domain-extension-policy.md` | domain-specific contract docs | retain |
| daily input UX policy | `docs/daily-input-ux-mvp.md` | `unified-input-ui-187.md`, `candidate-api-v1.md` | issue memo 吸収先 |
| daily input mode contract | `docs/daily-input-mode-contract-v1.md` | UX comparison / UI docs | retain |
| candidates API contract | `docs/candidate-api-v1.md` | daily input UI docs | retain |
| storage operation boundary | `docs/data-directory.md` | `migration.md`, `restore-mvp-draft.md`, `storage-unification-plan.md` | follow-up 統合候補 |
| storage unification history | `docs/storage-unification-plan.md` | `data-directory.md`, restore docs | historical record |
| backup / restore procedure | `docs/infra/restore-mvp-draft.md` | `backup-mvp-options.md`, `data-directory.md` | draft のため統合余地あり |
| cleanup taxonomy | `docs/cleanup-architecture.md` | `cleanup-pipeline.md`, `doc-drift-detection.md` | retain |
| cleanup execution model | `docs/cleanup-pipeline.md` | `cleanup-architecture.md`, toolchain baseline | retain |
| doc drift detector design | `docs/doc-drift-detection.md` | `cleanup-architecture.md`, `cleanup-pipeline.md` | retain |
| notification payload contract | `docs/ai-notification-contract-v1.md` | `infra/notify-wrapper.md` | retain |
| notify wrapper interface | `docs/infra/notify-wrapper.md` | `ai-notification-contract-v1.md`, Discord adapter contract | retain |
| Discord adapter contract | `docs/infra/discord-webhook-channel-contract.md` | `infra/notify-wrapper.md` | retain |
| canonical skill definitions | `docs/skills/*.md` | `.codex/skills/*/SKILL.md`, `.claude/skills/*/SKILL.md` | `#418` の統合検討対象 |

### 8.2 Immediate ownership observations

- `#417` で主に扱うべきなのは `ai-system-core` と、その比較対象である `AGENTS.md` `AI_GUIDE.md` `CLAUDE.md` である
- `#418` で主に扱うべきなのは `ai-runbook-skill` と `skill-*` cluster である
- `worker-coordination` は protocol child docs として retain 寄りだが、`#417` で親文書側の導線整理は必要である
- `#419` は ownership を決める issue ではなく、上記の決定後に index / stub / backlink を整える issue として読むのが自然である

## 9. Initial Consolidation Proposal

### 9.1 High-priority integrate candidates

| file | likely destination | rationale |
|---|---|---|
| `docs/AI_ROLE_POLICY.md` | new AI architecture / priming parent doc | role / workflow / dispatch の親文書候補へ寄せるため |
| `docs/AI_WORKFLOW.md` | new AI architecture / priming parent doc or child workflow section | `PLAYBOOK` と境界が近い |
| `docs/PLAYBOOK.md` | new AI architecture / daily flow parent doc | lifecycle と runbook の橋渡しを 1 本化したいため |
| `docs/WORKER_POLICY.md` | new AI architecture / priming parent doc | dispatch policy を role / workflow 文脈で読みやすくするため |
| `docs/CODEX_RUNBOOK.md` | parent runbook plus runtime-specific appendix | 共通手順が skills と重複しているため |
| `docs/git-branch-cleanup-cheatsheet.md` | parent runbook appendix | high-frequency operational note のため |
| `docs/skills/issue-create.md` | GitHub ops runbook or appendix | コマンド手順中心で runbook と近接するため |
| `docs/skills/issue-project-meta.md` | GitHub ops runbook or appendix | GitHub ops runbook とまとめやすいため |
| `docs/skills/minimal-safe-impl.md` | verification / execution runbook | 実行順序が `CODEX_RUNBOOK` と近接するため |
| `docs/skills/review-diff.md` | review runbook appendix | review 手順と一体で参照されやすいため |
| `docs/skills/review-preflight.md` | review runbook appendix | fixed procedure が runbook と近接するため |
| `docs/unified-input-ui-187.md` | `docs/daily-input-ux-mvp.md` | 既に parent doc を参照しており issue-specific policy を吸収しやすい |
| `docs/migration.md` | `docs/data-directory.md` or storage follow-up doc | migration note を storage docs に寄せやすいため |
| `docs/infra/restore-mvp-draft.md` | storage / backup runbook | `draft` のまま独立維持するより統合余地が高いため |

### 9.2 Primary retire candidates

| file | reason |
|---|---|
| `docs/issue-79-proposal-review.md` | canonical contract docs が成立済みで、review memo の役割が薄い |
| `docs/issue-213-daily-log-input-frictions.md` | daily input canonical docs と issue に役割が吸収されやすい |
| `docs/infra/ai-cli-discord-smoke-log.md` | docs というより verification log であり、issue / PR evidence に寄せやすい |

## 10. Handoff to Child Issues

| child issue | should consume from this inventory | should avoid touching first |
|---|---|---|
| `#417` | `ai-system-core`, `worker-coordination`, comparison-only entrypoint docs | event / heatmap / storage / notification clusters |
| `#418` | `ai-runbook-skill`, `skill-*`, GitHub ops and review flow docs | protocol specs, core architecture, domain contracts |
| `#419` | `proposed action` 列、integrate / stub / retire candidate 一覧、comparison-only docs | source-of-truth の再定義 |

`#416` の役割は「どの docs が何の concern を持つか」を見える化するところまでで止める。
実際の移設、stub 化、導線整理は各 child issue に委譲する。

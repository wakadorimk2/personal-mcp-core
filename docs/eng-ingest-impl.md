# eng domain GitHub Ingest — 実装責務定義 (#204)

> **スコープ注記**
> この文書は Issue #204 の実装 spec である。
> `eng` domain の概念設計は [#193] に委ねる（本文書では扱わない）。
> 外部保存戦略は [#150]、storage 単一化実装は [#189/#190/#191] で管理する。
>
> **この文書が定めるもの:**
> - 既存 `github_sync` MVP の責務と境界
> - 新 ingest 実装の責務・取り込み対象・除外条件・完了条件
> - `source/ref` 契約の適用ルール（受け入れ条件として固定）
> - Layer 1 / Layer 2 の分離と依存前提

---

## 1. 責務境界の定義

### 1.1 既存 `github_sync`（手動同期 MVP）

**担当:** `src/personal_mcp/tools/github_sync.py`

| 項目 | 現状 |
|---|---|
| 実行方式 | 手動実行（CLI: `github-sync` コマンド） |
| 取得対象 | GitHub API `/users/{username}/events` first page（最大 100 件） |
| 出力 | Event Contract v1 レコード、`domain: "eng"` 固定 |
| source 値 | `"github"` 固定 |
| dedup キー | `data.github_event_id`（既存 `source: "github"` レコードから検索） |
| skip 対象 | `WatchEvent` / `PublicEvent` / `MemberEvent` |

**責務の限界（MVP 意図どおり）:**
- 単一ユーザーの public events のみ（first page 上限あり）
- cron / webhook 常駐は含まない
- `source: "github-import"` による一括 import は含まない

### 1.2 本 Issue（#204）の新 ingest 実装

**担当:** 本 Issue で責務・完了条件を定義する。本体実装は follow-up Issue とする（後述）。

`github_sync` を「既存の手動同期 MVP」として保持しつつ、以下の責務を段階的に引き受ける:

- 取り込み対象の最小セットの明確化（Section 2）
- `source/ref` 契約の受け入れ条件への固定（Section 3）
- `eng` domain の event 化 `kind` 方針の明文化（Section 4）
- storage 依存を段階化した完了条件の設定（Section 5 / 6）

---

## 2. 取り込み対象の最小セット

### 2.1 対象イベント種別（優先順位付き）

| 優先 | GitHub event type | event 化 判断 | `kind` | `ref` 形式 |
|---|---|---|---|---|
| HIGH | `IssuesEvent` (closed) | Issue のクローズ → 節目 | `milestone` | `#<number>` |
| HIGH | `PullRequestEvent` (closed + merged) | PR マージ → 節目 | `milestone` | `PR#<number>` |
| HIGH | `PushEvent` | commit push → 成果物 | `artifact` | short SHA (7 文字以上) |
| MED | `IssuesEvent` (opened / other) | Issue の開始・更新 | `note` | `#<number>` |
| MED | `PullRequestEvent` (closed, not merged) | PR クローズ → 節目 | `milestone` | `PR#<number>` |
| MED | `PullRequestEvent` (opened / other) | PR の開始・更新 | `artifact` | `PR#<number>` |
| MED | `CreateEvent` | branch / tag 作成 | `artifact` | ─（`data.text` で表現） |
| LOW | その他の recognized type | 補足記録 | `note` | ─ |

### 2.2 除外対象（skip list）

以下は low-signal として取り込まない:

| GitHub event type | 除外理由 |
|---|---|
| `WatchEvent` | Star 付与のみ。activity signal として弱い |
| `PublicEvent` | repository 公開操作。頻度が低く eng activity として意味が薄い |
| `MemberEvent` | collaborator 変更。personal activity log の対象外 |

追加除外が必要になった場合は skip list を更新し、本文書に理由を記録する。

### 2.3 取り込み対象外（スコープ外）

- Organization events（`/orgs/{org}/events`）: 個人の activity log の対象外
- GitHub Actions / Deployments events: 対象の別 Issue での判断を待つ
- 複数 GitHub アカウントの統合: 単一アカウントが最小スコープ
- cron / webhook 常駐: 本 Issue の out of scope（follow-up Issue へ）

---

## 3. `source/ref` 契約の適用ルール（受け入れ条件）

> **正本:** `docs/mvp-contract-decisions.md` Section D

本 Issue の新 ingest 実装は以下を受け入れ条件として満たさなければならない。

### 3.1 `source` 値の適用

| 生成方式 | `source` 値 |
|---|---|
| `github_sync`（手動 or 自動の逐次同期）| `"github"` |
| 過去期間の一括 import（`github-import` 経路）| `"github-import"` |

`"github-import"` 経路の実装は本 Issue では行わない。ただし、将来の一括 import と逐次同期が同じ dedup ロジックで処理できるように `source` の区別を維持する。

### 3.2 `ref` 値の形式

| 対象 | `ref` 形式 | 例 |
|---|---|---|
| GitHub Issue | `"#<number>"` | `"#148"` |
| GitHub PR | `"PR#<number>"` | `"PR#42"` |
| GitHub commit | short SHA（7 文字以上） | `"abc1234"` |
| `CreateEvent` など ref が明示できない場合 | 省略（`data.text` で補う）| ─ |

複数参照が発生する場合はスペース区切り（先頭が主参照）で表現する。

### 3.3 dedup キー

逐次同期（`source: "github"`）の重複判定は `data.github_event_id` を使用する。

一括 import（`source: "github-import"`）の重複判定キーは、`source` の違いにより逐次同期と独立して管理できる。最終仕様は Layer 2 の完了条件として定義する（Section 6 参照）。

---

## 4. `eng` domain の `kind` 方針

> **正本:** `docs/kind-taxonomy-v1.md`

`eng` domain で GitHub activity を event 化する場合、以下の原則に従う。

### 4.1 kind 選択原則

- `kind` は cross-domain な軸であり、`eng` 固有語を `kind` として導入しない
- GitHub event type を `kind` の名前にしない（例: `push_event` は使わない）
- イベントが「何であるか」の抽象的型として v1 minimum kind set から選ぶ

### 4.2 マッピング方針（既存実装との整合）

現在の `github_sync` 実装のマッピングは以下の通りで、kind taxonomy v1 の設計意図と整合している:

| GitHub event | `kind` | 意図 |
|---|---|---|
| Issue クローズ / PR close | `milestone` | 節目・到達点 |
| Push / PR open / Create | `artifact` | 成果物の作成・更新 |
| Issue open 等 | `note` | 気づき・開始の記録 |
| その他認識外イベント | `note` | fallback |

`kind` の追加が必要になった場合は `docs/kind-taxonomy-v1.md` の Kind Add Rules に従う。

---

## 5. Layer 1 完了条件

**前提:** storage migration 状態に依存しない。`events.jsonl` または `events.db` への書き込みが可能な状態で達成できること。

- [ ] 取り込み対象（イベント種別・対象ソース・除外条件）の最小定義が明文化されている（→ Section 2）
- [ ] 既存 `github_sync` の責務（手動同期 MVP）と本 Issue の責務（新 ingest 実装）の境界が明文化されている（→ Section 1）
- [ ] `eng` domain で event 化する最小単位と `kind` 方針が定義されている（→ Section 4）
- [ ] `source/ref` 契約の適用ルールが明文化されている（→ Section 3）
- [ ] Layer 1 の完了条件が本文書として記録されており、レビュー可能な状態である

> **現状:** 本文書の作成により Layer 1 の doc 要件を満たす。
> 本体実装（新 ingest 実装）は別 follow-up Issue で行う。

---

## 6. Layer 2 完了条件

**前提:** `#189/#190/#191` の storage migration 進行状態と整合する。

- [ ] 保存経路（`events.db` 正本）の扱いが `#189/#190/#191` と矛盾しない形で定義されている
- [ ] `events.jsonl` 互換経路の移行条件が明文化されている
  - 互換期間: `#191`（dual-write 撤去）が完了するまで
  - 再生成条件: `events.db` が正本であり、欠損時は `events.db` から再生成する（`docs/storage-unification-plan.md` Failure recovery rule）
  - 復旧手順維持条件: `events.db` 欠損時は `events.jsonl` から再生成できる手順を維持する（`docs/storage-unification-plan.md` Failure recovery rule）
  - 撤去条件: `docs/storage-unification-plan.md` の Dual-write removal conditions すべて達成後
- [ ] 重複判定キーと保存先整合ルールの最終仕様が定義されている
  - 逐次同期（`source: "github"`）: `data.github_event_id` で dedup
  - 一括 import（`source: "github-import"`）: dedup キーの最終仕様は `#190/#191` 完了後に定義する
- [ ] Layer 2 の完了条件が `#190/#191` の進行状況と整合した状態でレビュー可能である

> **現状:** Layer 2 は `#190/#191` 未完了のため、上記は「将来の完了条件の定義」として記録する。
> 実装着手前に `#190/#191` の状態を確認し、本 Section を更新すること。

---

## 7. Out of scope（本 Issue では決めないこと）

- `eng` domain の概念設計（→ #193）
- 外部保存戦略の判断（→ #150）
- storage 単一化実装（→ #189/#190/#191）
- cron / webhook 常駐実装（follow-up Issue）
- 複数 GitHub アカウント・Organization events の同時統合（follow-up Issue）
- `source/ref` 契約の意味変更（人間レビュー必須）
- Event Contract v2 の新設

---

## 8. 後続 Issue 参照ガイド

| 後続作業 | 参照 |
|---|---|
| 新 ingest 本体実装 | 本文書 Section 2–4 を仕様として参照する follow-up Issue |
| storage 単一化との整合確認 | `docs/storage-unification-plan.md`、#190/#191 |
| `source/ref` 契約の詳細 | `docs/mvp-contract-decisions.md` Section D |
| `kind` 追加ルール | `docs/kind-taxonomy-v1.md` Kind Add Rules |
| Event Contract v1 schema | `docs/event-contract-v1.md` |

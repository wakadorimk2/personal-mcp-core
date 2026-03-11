# eng domain GitHub Ingest — 実装責務定義 (#204)

> **スコープ注記**
> この文書は Issue #204 の実装 spec である。
> `eng` domain の概念設計は [#193] と [`docs/eng-domain-concept.md`](./eng-domain-concept.md) に委ねる（本文書では扱わない）。
> 外部保存戦略は [#150]、storage 単一化実装は [#189/#190/#191] で管理する。
> #204 の完了条件は **spec / acceptance contract / boundary definition の固定** であり、
> runtime の ingest 実装完了は含まない。本体実装は follow-up Issue で行う。
> したがって、#204 は docs がレビュー可能になり follow-up 実装へ引き渡せる状態で close してよい。
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

**#204 を close してよい条件:**
- Section 2 から Section 5 の spec がレビュー可能な状態で固定されている
- 関連参照から本文書を辿れる
- follow-up 実装 Issue が、責務境界を再議論せず本文書を参照して着手できる

**#204 でやらないこと:**
- 新 ingest runtime 実装の追加
- 既存 `github_sync` の削除や置換
- #193 / #150 / #189 / #190 / #191 の責務の意味変更

---

## 2. 取り込み対象の最小セット

### 2.1 対象イベント種別（優先順位付き）

| 優先 | GitHub event type | event 化 判断 | `kind` | `ref` 形式 |
|---|---|---|---|---|
| HIGH | `IssuesEvent` (`action=closed`) | Issue のクローズ → 節目 | `milestone` | `#<number>` |
| HIGH | `PullRequestEvent` (`action=closed`, `merged=true`) | PR マージ → 節目 | `milestone` | `PR#<number>` |
| HIGH | `PushEvent` | commit push → 成果物 | `artifact` | head commit の short SHA（7 文字以上） |
| MED | `IssuesEvent` (`action=opened` / `reopened` / `edited`) | Issue の開始・再開・更新 | `note` | `#<number>` |
| MED | `PullRequestEvent` (`action=closed`, `merged=false`) | PR クローズ → 節目 | `milestone` | `PR#<number>` |
| MED | `PullRequestEvent` (`action=opened` / `reopened` / `edited` / `synchronize`) | PR の開始・再開・更新 | `artifact` | `PR#<number>` |
| MED | `CreateEvent` (`ref_type=branch` / `tag`) | branch / tag 作成 | `artifact` | ─（`data.*` で表現） |
| LOW | その他の event type（fallback 条件を満たすもの） | 補足記録 | `note` | ─ |

補足:

- ここで列挙する action は「新 ingest 実装で最小限サポートする粒度」であり、GitHub payload の全 action を列挙することは目的としない
- `PushEvent` が複数 commit を含む場合でも、`ref` は head commit の short SHA を主参照として 1 つだけ入れる
- `action` が上表に含まれない場合は、自動で取り込まず Section 2.2 / 2.3 の条件で扱う

### 2.2 fallback 取り込み条件

`LOW` の fallback は「recognized type なら何でも入れる」ための入口ではない。以下をすべて満たす場合のみ `note` として取り込む。

- `data.repo_full_name` を安定して保持できる
- `data.github_event_type` を保持できる
- `data.text` に人間が読める要約を安定生成できる

上記のいずれかを満たせない場合は fallback で取り込まず skip とする。

### 2.3 除外対象（skip list）

以下は low-signal として取り込まない:

| GitHub event type | 除外理由 |
|---|---|
| `WatchEvent` | Star 付与のみ。activity signal として弱い |
| `PublicEvent` | repository 公開操作。頻度が低く eng activity として意味が薄い |
| `MemberEvent` | collaborator 変更。personal activity log の対象外 |

追加除外が必要になった場合は skip list を更新し、本文書に理由を記録する。

### 2.4 取り込み対象外（スコープ外）

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

`ref` は「短い人間向け参照」を置く欄であり、repo 文脈・event type・action・GitHub 上の URL は `data.*` に保持する。
`ref` に URL や複数の文脈情報を詰め込まない。

| 対象 | `ref` 形式 | 例 |
|---|---|---|
| GitHub Issue | `"#<number>"` | `"#148"` |
| GitHub PR | `"PR#<number>"` | `"PR#42"` |
| GitHub commit | short SHA（7 文字以上） | `"abc1234"` |
| `CreateEvent` など ref が明示できない場合 | 省略（`data.text` で補う）| ─ |

複数参照が発生する場合はスペース区切り（先頭が主参照）で表現する。

補足ルール:

- `PushEvent` の `ref` は head commit の short SHA を主参照とする
- `PushEvent` が複数 commit を含む場合、commit 数や full SHA などの補足情報は `data.text` または `data.*` に保持する
- `CreateEvent` は `ref` を省略したまま、branch / tag の別と ref 名を `data.ref_type` / `data.ref_name` で保持する
- これらは新 ingest 実装の受け入れ条件であり、#204 自体は既存 `github_sync` の runtime 挙動変更を要求しない

### 3.3 downstream 利用のための `data.*` 最低限フィールド

Event Contract v1 の `data` は可変 payload とするが、新 ingest 実装では downstream 利用のため最低限以下の情報を保持する。

| key | 方針 |
|---|---|
| `data.github_event_id` | `source: "github"` / `"github-import"` の dedup 用。原則必須 |
| `data.github_event_type` | GitHub event type の記録。原則必須 |
| `data.repo_full_name` | `owner/repo` の repo 文脈。対象 scope 内では原則保持 |
| `data.action` | payload に action がある event で保持。取得不能なら省略可 |
| `data.html_url` | GitHub 上で人間が開ける stable URL が取れる場合に保持。`ref` には入れない |
| `data.head_sha` | `PushEvent` の full SHA。`ref` の主参照 short SHA を補足する |
| `data.commit_count` | `PushEvent` の commit 数。複数 commit の補足用 |
| `data.ref_type` | `CreateEvent` の branch / tag 区別 |
| `data.ref_name` | `CreateEvent` の ref 名 |

補足:

- この節は Event Contract v1 の schema 意味変更ではなく、#204 の新 ingest 実装における「最低限保持したい payload」の定義である
- `data.html_url` は stable な人間向け URL を優先し、安定 URL を構成できない event type では省略可とする

### 3.4 dedup キーと update policy

逐次同期（`source: "github"`）の重複判定は `data.github_event_id` を使用する。
同一 `data.github_event_id` を持つ既存 record がある場合は **skip** し、既存 event の上書き更新は行わない。

原則:

- 逐次同期は insert-only / skip とする
- 同一 event の再取得を理由に、既存 record の `text` / `data.*` / `tags` / `ref` を親切心で更新しない
- 後から情報補完が必要になった場合でも、逐次同期の update としては扱わず別 Issue / 別経路で判断する

一括 import（`source: "github-import"`）の重複判定キーは、`source` の違いにより逐次同期と独立して管理できる。最終仕様は Layer 2 の完了条件として定義する（Section 6 参照）。

---

## 4. `eng` domain の `kind` 方針

> **正本:** `docs/kind-taxonomy-v1.md`

`eng` domain で GitHub activity を event 化する場合、以下の原則に従う。

### 4.1 kind 選択原則

- `kind` は cross-domain な軸であり、`eng` 固有語を `kind` として導入しない
- GitHub event type を `kind` の名前にしない（例: `push_event` は使わない）
- イベントが「何であるか」の抽象的型として v1 minimum kind set から選ぶ

### 4.2 マッピング方針（既存実装を踏まえた新 ingest の受け入れ条件）

既存 `github_sync` の baseline を踏まえつつ、新 ingest 実装では以下を `kind` マッピングの受け入れ条件とする:

| GitHub event | `kind` | 意図 |
|---|---|---|
| `IssuesEvent` (`closed`) / `PullRequestEvent` (`closed`) | `milestone` | 節目・到達点 |
| `PushEvent` / `PullRequestEvent` (`opened` / `reopened` / `edited` / `synchronize`) / `CreateEvent` | `artifact` | 成果物の作成・更新 |
| `IssuesEvent` (`opened` / `reopened` / `edited`) | `note` | 気づき・開始の記録 |
| その他の event type | `note` or skip | fallback 条件を満たす場合のみ `note`、満たさなければ skip |

`kind` の追加が必要になった場合は `docs/kind-taxonomy-v1.md` の Kind Add Rules に従う。

---

## 5. Layer 1 完了条件

**前提:** runtime storage は `events.db` を正本とする。`events.jsonl` は recovery 用の再生成元/生成先としてのみ扱う。

- [ ] 取り込み対象（イベント種別・対象ソース・除外条件）の最小定義が明文化されている（→ Section 2）
- [ ] 既存 `github_sync` の責務（手動同期 MVP）と本 Issue の責務（新 ingest 実装）の境界が明文化されている（→ Section 1）
- [ ] `eng` domain で event 化する最小単位と `kind` 方針が定義されている（→ Section 4）
- [ ] `source/ref` 契約の適用ルールが明文化されている（→ Section 3）
- [ ] downstream 利用に必要な最低限の `data.*` が定義されている（→ Section 3.3）
- [ ] dedup の insert-only / skip 方針が明文化されている（→ Section 3.4）
- [ ] Layer 1 の完了条件が本文書として記録されており、レビュー可能な状態である
- [ ] 関連参照から本文書を辿れる状態になっている
- [ ] follow-up 実装 Issue が本文書を参照して着手できる状態である

> **Issue close 判断:** #204 は Layer 1 の各項目が満たされ、本文書が review 済みで follow-up 実装へ引き渡せる時点で close してよい。
> runtime の ingest 実装完了は #204 の完了条件に含めない。

---

## 6. Layer 2 完了条件

**前提:** `#189/#190/#191` は 2026-03-11 時点ですべて `CLOSED`。runtime storage は `events.db` 正本、`events.jsonl` は recovery 入力/出力という steady state にある。

- [ ] 保存経路（`events.db` 正本）の扱いが `#189/#190/#191` と矛盾しない形で定義されている
- [ ] `events.jsonl` 互換経路の移行条件が明文化されている
  - runtime 方針: 読み書きと dedup は `events.db` のみを参照する
  - 再生成条件: `events.db` が正本であり、欠損時は `events.db` から再生成する（`docs/storage-unification-plan.md` Failure recovery rule）
  - 復旧手順維持条件: `events.db` 欠損時は `events.jsonl` から再生成できる手順を維持する（`docs/storage-unification-plan.md` Failure recovery rule）
  - 互換経路の位置づけ: runtime fallback は持たず、明示的な recovery command に限定する
- [ ] 重複判定キーと保存先整合ルールの最終仕様が定義されている
  - 逐次同期（`source: "github"`）: runtime primary storage (`events.db`) 上で `data.github_event_id` により dedup する
  - 一括 import（`source: "github-import"`）: 本文書では最終仕様を固定しない。runtime の逐次 ingest とは別経路として follow-up issue で扱う
- [ ] Layer 2 の完了条件が `#190/#191` の進行状況と整合した状態でレビュー可能である

> **現状（2026-03-11）:** storage migration 前提は解消済みで、runtime は `events.db` を参照する。
> 以後の Layer 2 で残る論点は `source: "github"` の逐次 ingest と、別経路である `source: "github-import"` を同じ issue で扱うかどうかの scope 整理である。

---

## 7. Out of scope（本 Issue では決めないこと）

- `eng` domain の概念設計（→ #193, `docs/eng-domain-concept.md`）
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
| 新 ingest 本体実装 | 本文書 Section 2–5 を仕様として参照する follow-up Issue |
| storage 単一化との整合確認 | `docs/storage-unification-plan.md`、#190/#191 |
| `source/ref` 契約の詳細 | `docs/mvp-contract-decisions.md` Section D |
| `kind` 追加ルール | `docs/kind-taxonomy-v1.md` Kind Add Rules |
| Event Contract v1 schema | `docs/event-contract-v1.md` |
| `eng` domain concept / boundary | `docs/eng-domain-concept.md`、#193 |

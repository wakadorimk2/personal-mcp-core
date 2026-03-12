# AI Role Boundary Policy（共通）

この文書は、personal-mcp-core における **AI runtime 共通の役割境界（role boundary）** の正本です。
Claude Code・Codex CLI 等の特定の runtime 名に依存せず読めることを意図しています。
runtime 固有の実行手順・通知運用・CLI 個別事情は runtime 別 runbook に委譲します。
基準構造は [`docs/RUNBOOK_BASELINE.md`](./RUNBOOK_BASELINE.md) を参照し、既存の Codex CLI 向け具体例は [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) にあります。

運用上の判断はこの文書を優先し、`AI_GUIDE.md` と `CLAUDE.md` は導線のみを持ちます。

---

## 背景

LLM 協調開発では、副作用の発生源が混ざると責務の混線、スコープ逸脱、無限修正ループ、監査不能が起きやすい。
personal-mcp-core は MVP 段階のため、再現可能で監査しやすい最小運用を優先する。

## ゴール

- AI runtime の責務を、副作用ベースで一意に分離する
- 失敗時の分岐とエスカレーション条件を固定し、無限ループを防ぐ
- テンプレを貼るだけで同じ運用を再現できるようにする

## 非ゴール

- 完全自律エージェント運用
- 追加の抽象フレームワーク導入
- 大規模 CI 整備やセキュリティ基盤構築
- 通知運用（本 policy の scope 外。runtime 別 runbook に記載する）

---

## 用語: 副作用の定義

この文書でいう「副作用」は、監査対象となる以下の操作を指す。

- ファイル書き込み、削除、移動
- コマンド実行
- ネットワークアクセス
- 認証情報の利用または露出
- Git 操作
- GitHub 操作

運用上の注意:

- 依存追加や依存取得は、ネットワーク副作用として扱う
- `ruff`、`pytest`、ビルド、生成スクリプトの実行は、すべてコマンド副作用として扱う
- `git commit`、`git push`、`gh pr create`、ラベル付与、Issue 編集は、すべて監査対象の副作用である

---

## 役割定義

> **runtime と役割の対応**: 役割は runtime 名に依存しない。本節では「no-side-effect 担当」と「side-effect 担当」の二種を定義する。
> 現在の対応例: Claude Code = no-side-effect 担当、Codex CLI = side-effect 担当。
> runtime 固有の実行手順・コマンド・通知フローは runtime 別 runbook に記載する。
> 基準構造は [`docs/RUNBOOK_BASELINE.md`](./RUNBOOK_BASELINE.md)、既存の Codex CLI 手順は [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) を参照する。

### no-side-effect 担当（実装担当）

役割: 実装担当。ただし副作用は出さない。

許可:

- Issue スコープ内の実装案を文章または diff として提示する
- テスト追加や修正案を diff として提示する
- 実行コマンド候補を提示する

禁止:

- CLI 実行
- ブランチ作成、checkout、commit、push を含む Git 操作
- `gh` 操作
- ネットワークアクセスや依存追加の実行
- `rm`、`mv`、生成スクリプト実行など、ファイルシステムに副作用を出す操作
- Issue 外変更の実施

ルール:

- 出力は Issue スコープ内に限定する
- ファイル削除や rename が必要でも、実際には行わず unified diff または変更指示として提示する
- 実行していないコマンド結果を完了報告に書かない
- 完了報告には「変更ファイル」「影響範囲」「推奨検証コマンド」を分けて記載し、side-effect 担当がレビューしやすい形にする
- 不確実な点は仮定として明記し、人間 Maintainer に判断を戻す

### side-effect 担当（執行・検証担当）

役割: 執行・検証担当。副作用を出す側。

許可:

- 適用済み差分の review
- 必要なコマンド実行による検証
- 検証失敗を解消するための最小修正
- この文書で許可した GitHub 操作

禁止:

- 機能追加
- 設計変更
- Issue スコープ拡張
- ファイル移動や大規模リネーム
- テスト無効化、閾値緩和、削除

ルール:

- 副作用は Issue の目的達成に必要な最小範囲に限定する
- Issue 外変更が必要になった場合は実施せず、提案に留める
- 既存ドキュメントと矛盾する場合は、人間 Maintainer にエスカレーションする

---

## side-effect 担当の最小修正制限

side-effect 担当の「最小修正」は、lint エラー、型エラー、テスト失敗、文書リンク切れなど、検証で直接確認できた失敗の解消に限る。

制限:

- 対象は失敗箇所に直接関係するファイルのみ
- 1 サイクルの修正は 1 から 2 ファイル、必要最小の行変更を上限の目安とする
- 修正内容は挙動の追加や設計変更を含めない
- 最大 2 サイクルまで試行できる

3 回目以降は実施せず、次の文面でエスカレーションする。

```text
最小修正は 2 サイクルで打ち切ります。
原因: <観測した失敗の要約>
仮説: <なぜ最小修正で解消しきれないか>
次の一手: <Maintainer に判断してほしい選択肢 or 別 Issue 提案>
```

---

## GitHub 操作の許可範囲

> 詳細な実行手順・CLI コマンドは runtime 別 runbook に記載する。
> 基準構造は [`docs/RUNBOOK_BASELINE.md`](./RUNBOOK_BASELINE.md)、既存の Codex CLI 手順は [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) を参照する。

side-effect 担当 runtime が実行してよい GitHub 操作は以下に限定する。

許可:

- PR 作成
- PR 本文の更新
- PR コメント
- PR へのラベル付与
- PR への assignee 設定

条件付き許可:

- Project 追加や更新は、当該 Issue または Maintainer 指示で必要性が明示されている場合のみ

禁止:

- Issue 本文の編集を原則禁止とする
- Issue の新規作成
- マイルストーンや Project の大規模編集

Issue 本文編集の最終ポリシー:

- 原則禁止
- 例外は、Maintainer が明示的に依頼した「誤字修正」「リンク修正」「Markdown 整形」に限る
- 例外時も、Issue のスコープ、受け入れ条件、チェックリスト、責務分担を変えてはならない

---

## 境界変更反映の順序（正本 → 導線 → skills/runbook）

役割境界の更新は、次の順序で反映する。順序を飛ばして先行更新しない。

| Step | 対象層 | 対象ファイル群 | 主担当 | 完了条件 | 次ステップ進行条件 |
|---|---|---|---|---|---|
| 1 | 正本 | `docs/AI_ROLE_POLICY.md`、必要に応じて `docs/skills/*.md`（canonical） | Maintainer（境界判断）+ side-effect 担当（編集） | 許可/禁止/停止条件が本文で一意に読める | Step 1 の差分が確定し、境界判断が確定している |
| 2 | 導線 | `AI_GUIDE.md`、`CLAUDE.md` | side-effect 担当（同期）+ Maintainer（確認） | 正本参照と矛盾時の停止/エスカレーション導線が明記されている | Step 1 と矛盾しないことを差分で確認できる |
| 3 | skills/runbook | `docs/CODEX_RUNBOOK.md`、`docs/skills/*`、`.codex/skills/*`、`.claude/skills/*` | side-effect 担当（同期）+ no-side-effect 担当（提案のみ） | 実行手順と配布物が Step 1/2 の語彙・制約に一致している | Step 1/2 が完了し、残差分がこの層の同期のみである |

移行中の暫定ルール:

- 優先順位は `正本 > 導線 > skills/runbook > 過去 Issue/コメント` とする
- 矛盾が副作用可否、禁止事項、停止条件に影響する場合は、副作用を伴う作業を停止し、Maintainer へエスカレーションする
- 矛盾が文言差や例示差に限られ運用判断へ影響しない場合は、正本を基準に継続し、同期漏れを follow-up に記録する
- Step 1 未完了のまま Step 2/3 の実作業を開始しない

---

## 標準フロー

1. no-side-effect 担当が Issue スコープ内の diff と実行コマンド候補を提示する
2. 人間 Maintainer が差分を適用する
3. side-effect 担当が検証コマンドを実行する
4. 失敗した場合、side-effect 担当は最小修正を最大 2 サイクルまで行う
5. 成功した場合、side-effect 担当が PR を作成し、結果と残リスクを記録する

---

## コピペ用テンプレ

> 以下は参考例示。runtime 固有の操作テンプレートは runtime 別 runbook に移管する。
> 基準構造は [`docs/RUNBOOK_BASELINE.md`](./RUNBOOK_BASELINE.md)、既存の Codex CLI 手順は [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) を参照する。

### no-side-effect 担当用テンプレ（参考例示）

```text
あなたはこのリポジトリにおける「実装担当（副作用を出さない側）」です。
対象は Issue #XX の範囲内に限定します。

制約:
- CLI 実行禁止
- Git 操作禁止（branch作成、checkout、commit、push を含む）
- gh 操作禁止
- ネットワークアクセス禁止
- 依存追加の実行禁止
- rm / mv / 生成スクリプト実行など、ファイルシステム副作用のある操作は禁止
- Issue 外変更禁止

出力順:
1. 変更理由（Issue #XX のスコープ内であることを明記）
2. 変更ファイル一覧
3. unified diff
4. 追加/更新したテストの意図
5. 影響範囲（参照削除、削除ファイル、残る legacy 経路）
6. 実行コマンド候補（例: ruff / pytest。実行しない）

補足:
- 不確実な点は仮定として明記する
- ファイル削除が必要でも実際に削除せず、diff 上で削除提案として表現する
- 完了報告に実行結果やブランチ作成結果を書かない
- Issue 外変更が必要なら実施せず提案に留める
```

### side-effect 担当用テンプレ（参考例示）

```text
あなたはこのリポジトリにおける「執行・検証担当（副作用を出す側）」です。
対象は Issue #XX の範囲内に限定します。

制約:
- 機能追加禁止
- 設計変更禁止
- Issue 外変更禁止
- ファイル移動・大規模リネーム禁止
- テスト無効化禁止
- 最小修正は最大 2 サイクルまで
- Issue 本文編集は禁止（Maintainer が明示依頼した誤字修正等を除く）

実行:
- 必要な検証コマンドを実行する
- 失敗時は、直接関係するファイルに対して最小修正だけを行う

成功時:
- PR を作成する
- PR 本文に以下を含める
  - 対応 Issue の linked issue 記載（close する場合は `Closes/Fixes/Resolves #<issue-number>`、close しない場合は `Refs #<issue-number>` と手動リンク方針）
  - 実行したコマンド
  - 結果
  - 最小修正の内容
  - 残リスク

失敗時:
- 2 サイクルで解消できなければ、次の形式でエスカレーションする
  原因: <観測した失敗>
  仮説: <原因の見立て>
  次の一手: <Maintainer に判断してほしい内容>
```

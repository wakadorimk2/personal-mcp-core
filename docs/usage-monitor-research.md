# Usage Monitor Research — Issue #120

> 種別: 調査・提案（実装前）
> 対象 Issue: #120
> 更新日: 2026-03-06（Issue #131 追加調査反映）

---

## 目的

最小の CLI モニターで「Claude / Codex の使用制限ステータス（直近枠 + 週次枠）」を
5 分間隔で表示できるかを調査する。
この文書は調査結果と提案案の記録であり、実装の開始指示ではない。

---

## 表示対象項目

| 表示項目 | 説明 |
|----------|------|
| Claude 直近制限 | 公式表現 `session-based usage limit`（5時間枠）に達しているか |
| Claude 週次制限 | 公式表現 `weekly and monthly caps` のうち週次枠に達しているか |
| Codex 直近制限 | 公式表現 `every 5 hours` に達しているか |
| Codex 週次制限 | 公式表現 `shared weekly limit` に達しているか |

### 集計境界（today の定義）

- `today` は **モニター実行環境のローカルタイムゾーン** で日付判定する（例: JST 環境なら 00:00-23:59 JST）
- UTC 固定ではないため、異なるタイムゾーン環境間では日次集計値が一致しない場合がある

### 公式文言の固定（2026-03-06確認）

| サービス | 直近制限ラベル（公式） | 週次制限ラベル（公式） | 参考 |
|------|------|------|------|
| Claude | `session-based usage limit` | `weekly and monthly caps`（週次表示では weekly 部分のみ利用） | https://support.anthropic.com/en/articles/8324991-about-claude-s-pro-plan-usage |
| Codex | `every 5 hours` | `shared weekly limit` | https://help.openai.com/en/articles/11096431-codex-usage-limits-pricing-and-availability |

---

## 参考: 使用量集計の依存方針（旧要件）

この節は token/session 集計要件の調査結果として保持する。
制限ステータス（5時間枠/週次枠）の一次表示には直接使わない。

モニタースクリプト本体は **Python 標準ライブラリのみ** を使用し、新規依存は追加しない。

`ccusage` は外部オプションとして位置づける:

- `ccusage` がインストール済みであれば優先利用する（集計ロジックを外部に委ねる）
- 未インストールまたはコマンド失敗時は `~/.claude/projects/` 直接読取に自動フォールバックする
- どちらの経路でも、モニタースクリプト自体が新たなパッケージを要求しない

| 経路 | 条件 | モニター側の追加依存 |
|------|------|----------------------|
| ccusage 経由 | `ccusage` コマンドが実行可能 | なし（subprocess 呼び出しのみ） |
| 直接読取 | ccusage 不在または失敗 | なし（標準ライブラリのみ） |

---

## 参考: 使用量データ取得元比較（旧要件）

### A. Claude Code usage

#### A-1: `ccusage` CLI 利用（外部オプション）

| 項目 | 内容 |
|------|------|
| 取得元 | npm パッケージ `ccusage`（任意インストール） |
| コマンド例 | `ccusage daily --json` または `npx ccusage@latest` |
| 出力形式 | JSON（`daily[]`, `totals`, `daily[].modelBreakdowns[]` を確認） |
| 更新方法 | 5 分ごとにコマンド実行、結果を parse して表示 |
| 依存 | Node.js / npm が必要（モニター本体の依存ではない） |
| 長所 | 集計ロジック外部化、edge case 処理済み |
| 短所 | 外部依存、出力 schema が変更される可能性あり |

**検証結果（2026-03-06）:**
- `ccusage --help` / `ccusage daily --help` で `--json` が利用可能であることを確認
- 当日指定専用フラグ（`--today`）は確認できず、`--since YYYYMMDD` + `--until YYYYMMDD` の併用が日次絞り込み手段
- `npx --yes ccusage@latest daily --since <today> --until <today> --json --offline` で JSON 出力を確認
- 出力主要フィールド: `inputTokens`, `outputTokens`, `cacheCreationTokens`, `cacheReadTokens`, `totalTokens`, `modelBreakdowns[].modelName`

#### A-2: `~/.claude/projects/` 直接読取（標準フォールバック）

| 項目 | 内容 |
|------|------|
| 取得元 | `~/.claude/projects/<hash>/*.jsonl` |
| データ形式 | JSONL。`type=="assistant"` 行で `message.model` と `message.usage.*` を確認 |
| 更新方法 | 5 分ごとにファイルを glob して当日タイムスタンプのレコードを集計 |
| 依存 | Python 標準ライブラリのみ（`json`, `glob`, `datetime`） |
| 長所 | 外部依存なし、ccusage 不在でも動作する |
| 短所 | ファイル形式が非公式・変更リスクあり、glob 対象が多いと遅い |

**検証結果（2026-03-06）:**
- パス実在確認: `~/.claude/projects/-home-wakadori-personal-mcp-core/*.jsonl`
- 集計に使える主要フィールド（assistant 行）:
  - 日付判定: top-level `timestamp`（ISO8601）
  - モデル別: `message.model`
  - トークン: `message.usage.input_tokens`, `message.usage.output_tokens`
  - キャッシュ: `message.usage.cache_creation_input_tokens`, `message.usage.cache_read_input_tokens`
- 1 ファイル内に複数 `type`（`user`, `assistant`, `system`, `file-history-snapshot`, `last-prompt`）が混在するため、`assistant` 行のみを集計対象にする必要あり
- 実ファイル追補: 一部セッションでは `.../<session-id>/subagents/*.jsonl` も存在し、`isSidechain: true` のサブエージェント会話ログが別ファイルに分離される

---

### B. Codex CLI usage

#### B-1: `~/.codex/` セッションログ解析

| 項目 | 内容 |
|------|------|
| 取得元 | `~/.codex/history.jsonl` |
| データ形式 | JSONL（`session_id`, `ts`, `text`） |
| 更新方法 | `ts`（Unix seconds）をローカル日付境界でフィルタし、`session_id` の重複除外で当日セッション数を算出 |
| 依存 | Python 標準ライブラリのみ |
| 長所 | 外部依存なし |
| 短所 | 公式安定 schema とは限らず、履歴欠損時に過少計上の可能性あり |

**検証結果（2026-03-06）:**
- `~/.codex/` と `~/.codex/history.jsonl` の実在を確認
- `history.jsonl` 全行で `session_id` / `ts` / `text` を確認
- `ts` は Unix seconds（例: `1772791348 -> 2026-03-06 19:02:28 JST`）として日次判定に直接利用可能
- 例: 2026-03-06（JST）範囲で `unique_sessions_today=7` を算出できることを確認
- Codex 側トークン情報は `history.jsonl` には存在せず、「セッション数」用途に限定して利用するのが妥当

#### B-2: Codex 組み込みコマンド（`/status` 代替）

| 項目 | 内容 |
|------|------|
| 取得元 | `codex --help` / `codex resume --help` のコマンド一覧 |
| 出力形式 | ヘルプテキスト |
| 更新方法 | CLI ヘルプ確認 |
| 長所 | 公式経路であれば安定性が高い |
| 短所 | 日次 usage を直接返すサブコマンドは確認できず、履歴集計の代替にならない |

**検証結果（2026-03-06）:**
- `codex --help` のコマンド一覧（version: `0.111.0`）に `status` / `usage` / `report` 相当のサブコマンドは見当たらない
- `codex resume` / `codex fork` はセッション再開・分岐用で、当日集計出力は提供しない
- 現時点では B-1（`~/.codex/history.jsonl` 直接読取）を一次手段とするのが現実的

### C. 実ファイル構造の追補確認（Issue #131）

| 対象 | 実ファイル | 確認した形式 |
|------|------------|--------------|
| Claude main session | `~/.claude/projects/<project>/<session-id>.jsonl` | JSONL。top-level `type` ごとに構造が異なり、usage は assistant 行の `message.usage.*` |
| Claude subagents | `~/.claude/projects/<project>/<session-id>/subagents/*.jsonl` | JSONL。`isSidechain: true` を含む別ストリーム |
| Codex history | `~/.codex/history.jsonl` | JSONL。`session_id`, `ts`, `text` の3フィールド反復 |
| Codex補助ログ | `~/.codex/log/codex-tui.log` | プレーンテキストログ（セッション集計用の主データ源には不向き） |

---

## 最小 CLI モニター案

### 設計方針

- Python スクリプト 1 ファイル、標準ライブラリのみ（新規依存追加なし）
- 表示は **Claude 2項目 + Codex 2項目** のみ（合計4項目）
- 直近制限・週次制限のラベルは公式表現をそのまま使う（上表）
- 制限状態が取得できない場合は `N/A` を表示し、`0` や推定値で補完しない
- `os.system("clear")` + `print()` のみ（curses / rich 等不使用）
- 5 分（300 秒）ごとに自動更新
- 視認性向上のため、状態表示は `■` / `□` を使う

### 欠測値の表示方針（M2 反映）

データが取得できなかった場合の表示ルール:

| 状況 | 表示 |
|------|------|
| 公式ソースへのアクセス失敗 | `N/A` |
| レスポンスは取得したが parse 失敗 | `N/A (parse error)` |
| 制限に未到達 | `□ not reached` |
| 制限に到達 | `■ reached` |

`reached/not reached` と `N/A` は必ず区別して表示する。

Issue #131 で整理したエラー分類:

| ソース | 状態 | 表示 | 備考 |
|------|------|------|------|
| Claude official usage source | 取得不可（未認証/通信失敗） | `N/A` | 5時間・週次とも欠測 |
| Claude official usage source | parse 失敗 | `N/A (parse error)` | 部分取得時は取得できた項目のみ表示 |
| Codex official usage source | 取得不可（未認証/通信失敗） | `N/A` | 5時間・週次とも欠測 |
| Codex official usage source | parse 失敗 | `N/A (parse error)` | 部分取得時は取得できた項目のみ表示 |
| local logs (`~/.claude/projects/`, `~/.codex/history.jsonl`) | 制限状態フィールドなし | `N/A` | 制限到達判定の一次情報には使えない |

### 表示レイアウト案

全項目を取得できた場合:

```
AI Usage Monitor  (updated: 14:30)

Claude limits
  session-based usage limit (5h):   □ not reached
  weekly and monthly caps (weekly): ■ reached

Codex limits
  every 5 hours:        □ not reached
  shared weekly limit:  □ not reached
```

取得失敗がある場合:

```
AI Usage Monitor  (updated: 14:30)

Claude limits
  session-based usage limit (5h):   N/A
  weekly and monthly caps (weekly): N/A

Codex limits
  every 5 hours:        N/A (parse error)
  shared weekly limit:  N/A (parse error)
```

### 疑似コード構造

```python
# 疑似コード（実装コードではない）

SENTINEL = "N/A"

def render_status(reached: bool | None) -> str:
    # None は欠測
    if reached is None:
        return SENTINEL
    return "■ reached" if reached else "□ not reached"

def get_claude_limits() -> dict:
    # 公式ソースから `session-based usage limit` と `weekly and monthly caps` を取得
    # 取得不可: {"short_window": None, "weekly": None}
    pass

def get_codex_limits() -> dict:
    # 公式ソースから `every 5 hours` と `shared weekly limit` を取得
    # 取得不可: {"short_window": None, "weekly": None}
    pass

def render(claude: dict, codex: dict) -> None:
    # os.system("clear")
    # 4項目のみ表示し、各項目は render_status() を通して描画する
    pass

# メインループ
# while True:
#   render(get_claude_limits(), get_codex_limits())
#   time.sleep(300)
```

---

## personal-mcp-core 統合の可能性

将来的には以下が考えられる（現時点では実装しない）:

- usage イベントを JSONL に記録し、event-contract-v1 形式で蓄積する
- `domain: "ai_usage"`, `kind: "token_summary"` 等のイベントとして append-only で保存
- MCP ツールとして `get_ai_usage_today` を expose する

これらは Issue #120 スコープ外であり、別 Issue として検討する。

---

## Issue #131 検証結果サマリ

| ソース | 取得手段 | 必要フィールド | 既知の制約 |
|---------|----------|----------------|------------|
| Claude official usage source | 公式Web表示（認証後） | `session-based usage limit`, `weekly and monthly caps` の状態 | 認証が必要。取得経路を別途実装する必要あり |
| Codex official usage source | 公式Web表示（認証後） | `every 5 hours`, `shared weekly limit` の状態 | 認証が必要。取得経路を別途実装する必要あり |
| `~/.claude/projects/` | `~/.claude/projects/*/*.jsonl`（必要に応じて `subagents/*.jsonl`）を直接 parse | `message.usage.*`, `message.model` など | 使用量は取れるが「制限到達状態」は直接取れない |
| `~/.codex/history.jsonl` | ローカルJSONL直接parse | `session_id`, `ts`, `text` | セッション履歴は取れるが「制限到達状態」は直接取れない |

---

## 残課題（実装時判断）

| 項目 | 内容 | 影響度 | 対応案 |
|---------|------|--------|--------|
| 制限状態の一次取得経路 | 公式ページ表現をそのまま使うため、認証付き取得方式が必要 | 高 | 公式API/CLIの公開状況を確認し、可能な手段を確定する |
| 公式文言の固定運用 | 文言変更時に表示ラベルが古くなるリスク | 中 | ラベル文字列を定数化し、見直し手順を運用に追加する |
| 週次境界のタイムゾーン | 週次リセット境界がサービス側TZに依存する可能性 | 中 | 取得元が返す次回リセット時刻を優先表示する |

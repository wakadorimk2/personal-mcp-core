# Usage Monitor Research — Issue #120

> 種別: 調査・提案（実装前）
> 対象 Issue: #120
> 更新日: 2026-03-06（Issue #131 追加調査反映）

---

## 目的

最小の CLI モニターで「Claude Code トークン / Codex セッション / モデル別使用量」を
5 分間隔で表示できるかを調査する。
この文書は調査結果と提案案の記録であり、実装の開始指示ではない。

---

## 表示対象項目

| 表示項目 | 説明 |
|----------|------|
| Claude tokens today | 当日の入力・出力トークン合計 |
| model usage | モデル別（opus / sonnet 等）のトークン内訳 |
| Codex sessions today | 当日起動したセッション数 |

### 集計境界（today の定義）

- `today` は **モニター実行環境のローカルタイムゾーン** で日付判定する（例: JST 環境なら 00:00-23:59 JST）
- UTC 固定ではないため、異なるタイムゾーン環境間では日次集計値が一致しない場合がある

---

## 依存方針（M1 反映）

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

## データ取得元比較

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
- `ccusage` は任意外部ツール: 利用可能であれば A-1 を採用し、そうでなければ A-2 に自動フォールバック
- Codex データが取得できない場合は `N/A` を表示し、`0` で誤魔化さない（M2）
- `os.system("clear")` + `print()` のみ（curses / rich 等不使用）
- 5 分（300 秒）ごとに自動更新
- 視認性向上のため、モデル別使用量は `■` / `□` ベースの固定幅バーで表示する

### 欠測値の表示方針（M2 反映）

データが取得できなかった場合の表示ルール:

| 状況 | 表示 |
|------|------|
| ccusage / 直接読取のどちらも失敗 | `N/A` |
| `~/.codex/` が存在しない | `N/A` |
| ログは存在するが解析失敗 | `N/A (parse error)` |
| 当日レコードが 0 件（実際に使用なし） | `0`（これは正常値） |

「0 件で使用なし」と「取得失敗」は区別して表示する。

Issue #131 で整理したエラー分類:

| ソース | 状態 | 表示 | 備考 |
|------|------|------|------|
| ccusage | `command not found` / 実行失敗（非0） | 直接読取へフォールバック（失敗時は `N/A`） | `ccusage` 単独失敗は即 `N/A` 固定にしない |
| ccusage | JSON parse 失敗 | `N/A (parse error)` | 直接読取へフォールバック可能なら継続 |
| `~/.claude/projects/` | ディレクトリ不在 / 読み取り不可 | `N/A` | 欠測扱い |
| `~/.claude/projects/` | JSONL parse 失敗 | `N/A (parse error)` | 行単位スキップ時は正常値と要区別 |
| `~/.codex/history.jsonl` | ファイル不在 | `N/A` | Codex セッション不明 |
| `~/.codex/history.jsonl` | parse 失敗（`session_id`/`ts` 抽出不可） | `N/A (parse error)` | ログ存在時の解析失敗 |

### 表示レイアウト案

Codex データが取得できない場合:

```
AI Usage Monitor  (updated: 14:30)

Claude tokens (today)  [source: ccusage]
  total: 142,384
  model usage:
    claude-opus-4-6    ■■■■■■■□□□□□  69%  98,234
    claude-sonnet-4-6  ■■■□□□□□□□  31%  44,150

Codex sessions (today): N/A
  (log source unavailable — see ~/.codex/)
```

Codex データが取得できた場合:

```
AI Usage Monitor  (updated: 14:30)

Claude tokens (today)  [source: direct ~/.claude/]
  total: 142,384
  model usage:
    claude-opus-4-6    ■■■■■■■□□□□□  69%  98,234
    claude-sonnet-4-6  ■■■□□□□□□□  31%  44,150

Codex sessions (today): 3
  latest:             14:12
```

### 疑似コード構造

```python
# 疑似コード（実装コードではない）

SENTINEL = "N/A"

def render_bar(ratio: float, width: int = 12) -> str:
    # ratio (0.0-1.0) を固定幅バーへ変換する
    filled = max(0, min(width, int(ratio * width)))
    return ("■" * filled) + ("□" * (width - filled))

def get_claude_usage() -> dict:
    # 1. ccusage が利用可能か試みる
    #    subprocess.run(["ccusage", ...], capture_output=True, timeout=10)
    #    成功: JSON parse して返す、source="ccusage"
    # 2. 失敗（FileNotFoundError / returncode != 0）:
    #    ~/.claude/projects/*/*.jsonl を glob
    #    当日タイムスタンプのレコードを集計して返す、source="direct"
    # 3. どちらも失敗: {"total": SENTINEL, "by_model": {}, "source": SENTINEL}
    pass

def get_codex_sessions() -> dict:
    # ~/.codex/ が存在しなければ {"count": SENTINEL, "latest": SENTINEL} を返す
    # 存在する場合: 当日セッションファイルを探して集計
    # parse 失敗: {"count": SENTINEL, "latest": "N/A (parse error)"}
    pass

def render(claude: dict, codex: dict) -> None:
    # os.system("clear")
    # model usage は `render_bar()` で可視化して print()
    # SENTINEL 値はそのまま文字列として表示（0 に変換しない）
    pass

# メインループ
# while True:
#   render(get_claude_usage(), get_codex_sessions())
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
| `ccusage` | `ccusage daily --since YYYYMMDD --until YYYYMMDD --json`（または `npx ccusage@latest`） | `daily[].inputTokens`, `daily[].outputTokens`, `daily[].modelBreakdowns[].modelName`, `totals.totalTokens` など | CLI 非導入環境では利用不可。schema 変更リスクあり |
| `~/.claude/projects/` | `~/.claude/projects/*/*.jsonl`（必要に応じて `subagents/*.jsonl`）を直接 parse | `timestamp`, `message.model`, `message.usage.input_tokens`, `message.usage.output_tokens`（必要に応じて cache 系） | 非公式ログ形式。`assistant` 以外の行が混在 |
| `~/.codex/` | `~/.codex/history.jsonl` を直接 parse | `session_id`, `ts` | セッション数集計は可能。トークン情報は取得不可 |

---

## 残課題（実装時判断）

| 項目 | 内容 | 影響度 | 対応案 |
|---------|------|--------|--------|
| キャッシュトークン扱い | `cache_creation_input_tokens` / `cache_read_input_tokens` を表示 total に含めるか | 低 | 先に表示仕様を決める |
| `ccusage` 実行経路 | `ccusage` 未導入時に `npx` を使うか、即 direct fallback するか | 低 | 実行時間とネットワーク依存で選択 |
| バー表示仕様 | プログレスバーの分母（モデル合計=100% か、固定上限か）をどちらにするか | 低 | まずはモデル合計100%基準で開始 |

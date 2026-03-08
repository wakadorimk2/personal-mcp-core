# personal-mcp-core

## What is this

個人の活動をローカルに append-only で記録する、CLI ベースのセルフ観測ツール。
ゲームセッション・気分・作業ログなどを共通の JSONL イベント形式で保存し、タイムライン表示やドメイン別フィルタリングができる。
設計思想・哲学的背景については [`docs/design-principles.md`](./docs/design-principles.md) を参照。

---

## Quick start

```bash
# インストール
pip install -e .

# eng / worklog など明示サポート domain のイベントを追加する
python -m personal_mcp.server event-add "設計メモを書いた" \
  --domain=worklog --tags=design,docs

# 気分を記録する
python -m personal_mcp.server mood-add "少し疲れた" --tags=tired

# 日付ごとのタイムラインを一覧する
python -m personal_mcp.server event-list --date 2026-03-03

# PoE2 の記録を追加する（互換用の専用コマンドも残している）
python -m personal_mcp.server poe2-log-add "アトラスの外縁でボス撃破" \
  --kind=milestone --tags=atlas,boss

# PoE2 Client.txt を監視してエリア遷移を自動記録する
python -m personal_mcp.server poe2-watch --client-log /path/to/Client.txt
```

動作確認:

```bash
python -m personal_mcp.server event-list --date $(date +%Y-%m-%d)
```

## Daily operation via Make

日常運用の最小導線は `make` でも実行できる。

```bash
# 実運用データは repo 外に置く（例）
export DATA_DIR="$HOME/.local/share/personal-mcp"

# web UI 起動
make run DATA_DIR="$DATA_DIR" PORT=8080

# 最小ログ追加（TEXT は必須）
make log DATA_DIR="$DATA_DIR" TEXT="朝会メモを記録"

# 当日ログ確認
make today DATA_DIR="$DATA_DIR"

# 日次サマリー生成（UTC日付）
make summary DATA_DIR="$DATA_DIR" DATE="$(date -u +%F)"

# 上記導線の最小疎通確認
make smoke DATA_DIR="$DATA_DIR" DATE="$(date -u +%F)"
```

`DATA_DIR` を渡さない場合は CLI の保存先解決（`--data-dir` > `PERSONAL_MCP_DATA_DIR` > XDG 既定）に従う。`repo/data/` は開発・テスト用であり、実運用の保存先には使わない。

`make check` / `make test` / `make help` の拡張はこの Issue の対象外（follow-up 扱い）。

---

## Data storage

ストレージ境界導入後（#189）の現状は、導線ごとの read/write を
`src/personal_mcp/storage/events_store.py` に統一している。

| 導線 | 現在の参照先 |
|---|---|
| CLI (`event-add` / `event-list` / `event-today`) | storage 境界（primary: `events.db`） |
| Web入力 (`web-serve` の `/events` / `/events/ui`) | storage 境界（primary: `events.db`） |
| summary (`summary-generate` / dashboard集計) | storage 境界（primary: `events.db`） |

移行期間は `events.jsonl` を互換経路として維持する（dual-write + fallback read）。
単一ストレージ化の方針・移行段階・障害復旧ルールは [`docs/storage-unification-plan.md`](./docs/storage-unification-plan.md) を参照。

| 優先順 | 解決方法 |
|---|---|
| 1 | `--data-dir` フラグ |
| 2 | `PERSONAL_MCP_DATA_DIR` 環境変数 |
| 3 | XDG 既定: `~/.local/share/personal-mcp/` |

`repo/data/` は開発・テスト・サンプル専用。実ユーザーデータを置かない。

詳細: [`docs/data-directory.md`](./docs/data-directory.md)

---

## Event model

イベントの保存契約は **[Event Contract v1](./docs/event-contract-v1.md)** に従う。

**必須フィールド**: `v`（`1` 固定）、`ts`（ISO 8601 タイムゾーン付き）、`domain`、`kind`（[kind taxonomy](./docs/kind-taxonomy-v1.md)）、`data`。
**推奨フィールド**: `tags`、`source`、`ref`（省略可）。

タイムスタンプは UTC で保存（`datetime.now(timezone.utc).isoformat()`）。ドキュメント例は JST（`+09:00`）表記。

記録例:

```json
{
  "v": 1,
  "ts": "2026-03-04T18:00:00+09:00",
  "domain": "eng",
  "kind": "note",
  "data": { "text": "MCP adapterの調査メモ" },
  "tags": ["research"],
  "source": "manual"
}
```

詳細・legacy record との互換方針: [Event Contract v1](./docs/event-contract-v1.md)

---

## Supported domains

| domain | 説明 |
| --- | --- |
| `poe2` | Path of Exile 2 の活動記録 |
| `mood` | 気分・体調記録 |
| `general` | 分類不要なメモや雑記 |
| `eng` | エンジニアリング全般（調査・設計・学習など） |
| `worklog` | 作業記録・進捗ログ |

`event-add` が受け付ける domain は上記 allowlist のみ。追加条件: [`docs/domain-extension-policy.md`](./docs/domain-extension-policy.md)

`kind` 推奨値（`eng` / `worklog`）:

| kind | 用途 |
| --- | --- |
| `note` | 調査メモ、気づき、短い記録 |
| `session` | 作業セッション、切り分け、実施ログ |
| `milestone` | 方針確定、区切り、到達点 |

---

## Development

```bash
# 開発用インストール
pip install -e ".[dev]"

# コードチェック
ruff check .

# 自動修正
ruff check . --fix

# フォーマット
ruff format .

# テスト
pytest

# AI_GUIDE.md の同期確認
diff AI_GUIDE.md src/personal_mcp/AI_GUIDE.md
```

**構成:**

```
src/personal_mcp/
├── server.py               # CLIエントリーポイント
├── tools/event.py          # 共通イベント記録・一覧
├── tools/poe2_client_watcher.py  # PoE2 Client.txt 監視
├── storage/jsonl.py        # 追記型JSONLストレージ
├── adapters/mcp_server.py  # MCP system context adapter
└── core/guide.py           # AI_GUIDE.md ローダー
```

**貢献の歓迎範囲:**

- バグ修正・型エラー修正
- テストの追加・改善
- ドキュメントの改善

機能追加は事前にIssueで議論してください。

### 互換性ポリシー（MVP期間中）

> 詳細・背景: [Issue #19](https://github.com/wakadorimk2/personal-mcp-core/issues/19)

- **保証**: JSONL イベント形式（破壊的変更時は `schema_version` フィールド追加 + ワンタイム移行スクリプト同伴）
- **保証しない**: CLI コマンド名、内部モジュール構造、MCP アダプター IF、設定ファイル形式

---

## Documentation

| ドキュメント | 内容 |
|---|---|
| [`docs/design-principles.md`](./docs/design-principles.md) | 設計思想・Architecture North Star（哲学的背景） |
| [`docs/event-contract-v1.md`](./docs/event-contract-v1.md) | イベント保存契約の正典 |
| [`docs/daily-input-ux-mvp.md`](./docs/daily-input-ux-mvp.md) | daily use UI 主導線（ヒートマップ直下入力）のMVP方針 |
| [`docs/kind-taxonomy-v1.md`](./docs/kind-taxonomy-v1.md) | `kind` フィールド分類 |
| [`docs/data-directory.md`](./docs/data-directory.md) | データ保存先の詳細ルール |
| [`docs/storage-unification-plan.md`](./docs/storage-unification-plan.md) | `events.db` / `events.jsonl` 単一化方針（#185） |
| [`docs/domain-extension-policy.md`](./docs/domain-extension-policy.md) | domain 拡張条件 |
| [`docs/architecture.md`](./docs/architecture.md) | 技術的アーキテクチャ |

---

## Privacy / License

- 個人の活動データはローカルに保存し、非公開。外部送信機能は現状ない。
- 集合統計・外部送信は明示オプトインのみ。
- ライセンス: 未定。個人利用を主軸に検討中。

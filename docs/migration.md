# コマンド移行方針

## poe2 専用コマンドの位置づけ

`poe2-log-add` と `poe2-log-list` は、汎用イベントコマンドが整備される以前に追加されたコマンドである。
現在は同等の操作を汎用コマンドで行える。

## 対応表

| 旧コマンド      | 対応する汎用コマンド        |
|----------------|-----------------------------|
| `poe2-log-add` | `event-add --domain poe2`   |
| `poe2-log-list`| `event-list --domain poe2`  |

## legacy データの扱い原則

- `data/poe2/logs.jsonl` は legacy パスとして削除済みであり、正式正本へ戻さない
- データ移行は行わない（追記のみ原則・不可逆ログの思想に沿う）
- 旧フォーマットの再導入もしない

## 本リポジトリでの現状

- `data/poe2/logs.jsonl` は実運用データが存在しないため削除済み。正式正本へ復元しない。
- `src/personal_mcp/tools/poe2_log.py` は legacy 実装として削除した。代替経路は `event-add --domain poe2` / `event-list --domain poe2`。
- `server.py` の `poe2-log-add` / `poe2-log-list` サブコマンドは引き続き動作するが、内部実装は汎用 `event_add` / `event_list` を使用している。

## ローカル正本の保存先変更

- 旧: `data/events.jsonl`（repo 内の相対パス）
- 新: XDG 既定の `~/.local/share/personal-mcp/events.jsonl`
- 優先順位: `--data-dir` > `PERSONAL_MCP_DATA_DIR` > XDG 既定

`repo/data/` は開発・テスト・例示用であり、実運用データの正本ではない。
既存の `data/events.jsonl` は移行元としてのみ扱い、実運用では repo 外の `data-dir` へ移す。

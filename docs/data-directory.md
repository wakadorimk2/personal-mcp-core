# repo 内 `data/` の位置づけと運用ルール

> 保存先解決ロジックの仕様は [`docs/architecture.md`](./architecture.md) を参照。
> docs 全体の入口は [`docs/README.md`](./README.md) を参照。

## 定義

`repo/data/` は **開発・テスト・サンプル専用のデータ置き場**。
個人ログの正本は置かない。実運用のユーザーデータを Git 管理対象に含めない。

ユーザーデータは常に repo 外の `data-dir` に保存する。

## 許可されるもの

- 開発・テスト用 fixture
- サンプルデータ・例示用 JSONL
- docs や再現手順から参照する小さな同梱データ

## 禁止されるもの

- 実ユーザーログの正本
- バックアップ成果物
- 復元成果物
- 個人運用で増え続ける永続データ

## 運用ルール

1. ユーザーデータは常に repo 外の `data-dir` に置く。
2. `repo/data/` は配布・検証に必要な小さな非正本データのみ置く。
3. `repo/data/` を実運用の保存先として案内・設定しない。

## 将来のバックアップ/復元との整合（#56/#57）

- バックアップ対象: repo 外の `data-dir` のみ
- 復元先: repo 外の `data-dir` のみ
- `repo/data/` はバックアップ・復元の対象外

## 保存先解決との整合（#54）

保存先解決の優先順位: `--data-dir` > `PERSONAL_MCP_DATA_DIR` > XDG 既定

`repo/data/` はこの解決チェーンに含まれない。

## runtime storage steady state

storage 単一化後の runtime は、`events.db` を正本として扱う。

- runtime の read/write は `events.db` のみを参照する
- dedup も runtime primary storage (`events.db`) 上で行う
- `events.jsonl` は通常運用の fallback ではなく、明示実行された recovery 入力/出力に限定する
- `storage-db-to-jsonl` / `storage-jsonl-to-db` は recovery-only 保守 command として維持する

recovery rule:

- `events.jsonl` 欠損時は `events.db` から再生成する
- `events.db` 欠損時は `events.jsonl` から再生成できる手順を維持する
- 不一致検出時は `events.db` を優先し、差分を記録したうえで再生成する

## legacy path / command migration

旧運用との整合は次の方針で扱う。

- `poe2-log-add` / `poe2-log-list` は legacy command として扱う
- 同等操作は `event-add --domain poe2` / `event-list --domain poe2` へ寄せる
- `data/poe2/logs.jsonl` は正式正本へ戻さない
- `repo/data/` は開発・例示用のままとし、実運用正本へ昇格させない

## restore checklist (MVP)

復元の最小方針:

- 復元元は別ディスク上のバックアップ
- 復元先は常に repo 外の `data-dir`
- `repo/data/` は復元対象に含めない
- `rsync --delete` は使わない

復元後の確認:

```sh
ls -lh <data-dir>/
ls -lh <data-dir>/events.db
personal-mcp event-list --n 10 --data-dir <data-dir>
```

必要な場合だけ recovery 用 command を明示実行する。通常運用の runtime fallback としては使わない。

```sh
personal-mcp storage-db-to-jsonl --dry-run --json --data-dir <data-dir>
personal-mcp storage-jsonl-to-db --dry-run --json --data-dir <data-dir>
```

```sh
personal-mcp storage-db-to-jsonl --data-dir <data-dir>
personal-mcp storage-jsonl-to-db --data-dir <data-dir>
```

関連比較表は [`docs/infra/backup-mvp-options.md`](./infra/backup-mvp-options.md) を参照。

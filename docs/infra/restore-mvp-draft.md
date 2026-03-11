# バックアップからの復元手順（MVPドラフト）

この文書は、端末故障や誤操作の際に、repo 外の `data-dir` をバックアップから復元するための **最小手順ドラフト** である。

バックアップ方式の選定は [`backup-mvp-options.md`](./backup-mvp-options.md) を参照。
DR 自動化・常時同期・クラウド運用は扱わない。

---

## 前提

- **正本（primary）**: repo 外の `data-dir`
  - パス解決の優先順位: `--data-dir` > `PERSONAL_MCP_DATA_DIR` > XDG 既定（詳細は [`architecture.md`](../architecture.md)）
- **復元元**: 別ディスク上の rsync バックアップ
- **復元先**: repo 外の `data-dir`（上記の正本と同じ場所）
- `repo/data/` はバックアップ・復元の **対象外**

以下の手順では `<data-dir>` を正本のパス、`<backup-dir>` をバックアップ先のパスとして読み替える。

---

## 復元前に確認すること

### 1. 正本 data-dir のパスを確認する

優先順位は `--data-dir` > `PERSONAL_MCP_DATA_DIR` > XDG 既定である。

- ふだん `--data-dir` を付けて実行している場合:
  その指定先を正本として扱う
- `--data-dir` を付けておらず、`PERSONAL_MCP_DATA_DIR` を設定している場合:
  その環境変数の値を正本として扱う
- どちらも使っていない場合:
  XDG 既定の `~/.local/share/personal-mcp/`、または `$XDG_DATA_HOME/personal-mcp/` を正本として扱う

```sh
echo $PERSONAL_MCP_DATA_DIR
echo $XDG_DATA_HOME
# 未設定なら XDG 既定は ~/.local/share/personal-mcp
```

### 2. バックアップのタイムスタンプを確認する

```sh
ls -lh <backup-dir>/
```

最終バックアップ時点より後に正本に追記があった場合、その分は復元で回収できない。

### 3. 正本の現状を確認する

```sh
ls -lh <data-dir>/
wc -l <data-dir>/events.jsonl
```

正本がまだ読み取れる状態であれば、復元前に現状を別の場所に退避しておくことを検討する。

---

## 復元手順（rsync の場合）

### 正本全体を復元する場合

```sh
rsync -av <backup-dir>/ <data-dir>/
```

### 特定ファイルのみ復元する場合

```sh
rsync -av <backup-dir>/events.jsonl <data-dir>/events.jsonl
```

---

## 復元時の注意点（append-only を壊さない）

このシステムのログは **append-only** として扱う。

注意点:

- **`rsync --delete` は使わない**
  バックアップ後に正本側で追記されたファイルが削除される。`rsync` のデフォルト（`--delete` なし）を維持する。

- **バックアップが正本より古ければ、その差分は回収できない**
  バックアップ後の追記分は、手動での再入力が必要になる場合がある。

- **復元は既存ファイルへの上書きになりうる**
  上書きは不可逆である。実行前に現状のコピーを別の場所に退避することが望ましい。

- **過去レコードの改変を目的とした操作は行わない**
  復元はデータの回収であり、内容の修正ではない。

---

## 復元後の確認手順

### 1. ファイルの存在と行数を確認する

```sh
ls -lh <data-dir>/
wc -l <data-dir>/events.jsonl
```

### 2. 最新レコードを目視確認する

```sh
tail -n 5 <data-dir>/events.jsonl
```

### 3. 片方向欠損時は migration tool で再生成する

`events.db` / `events.jsonl` どちらかが欠損した場合は、まず dry-run で件数差分を確認する。

```sh
# events.db -> events.jsonl 再生成（dry-run）
personal-mcp storage-db-to-jsonl --dry-run --json --data-dir <data-dir>

# events.jsonl -> events.db 再生成（dry-run）
personal-mcp storage-jsonl-to-db --dry-run --json --data-dir <data-dir>
```

dry-run の結果が想定どおりであれば、実際に再生成する。

```sh
# events.db を正として events.jsonl を再生成
personal-mcp storage-db-to-jsonl --data-dir <data-dir>

# events.jsonl を元に events.db を再生成
personal-mcp storage-jsonl-to-db --data-dir <data-dir>
```

> **Note**: `storage-jsonl-to-db` は JSONL の内容を **忠実に再構築** する（dedup なし）。
> JSONL に重複レコードが含まれる場合、DB にも同数のレコードが挿入される。
> 将来の重複排除は runtime の `github-sync` / `github-ingest` が担う。
> この挙動は「復元はデータの回収であり、内容の修正ではない」という原則と一致する。

### 4. `event-list` で読み取れることを確認する

```sh
personal-mcp event-list --n 10 --data-dir <data-dir>
```

ドメイン別に確認する場合:

```sh
personal-mcp event-list --n 10 --domain eng --data-dir <data-dir>
personal-mcp event-list --n 10 --domain mood --data-dir <data-dir>
```

特定の日付以降を確認する場合:

```sh
personal-mcp event-list --since YYYY-MM-DD --data-dir <data-dir>
```

---

## 復旧チェックリスト

- [ ] バックアップのタイムスタンプを確認した
- [ ] 正本の現状（残存・消失・破損の範囲）を確認した
- [ ] バックアップ後の追記分の有無を確認した（回収できないデータの把握）
- [ ] 復元先の data-dir が repo 外であることを確認した
- [ ] `--delete` を使わない形で rsync を実行した
- [ ] 復元後、`ls` でファイルの存在を確認した
- [ ] 復元後、`wc -l` でレコード数を確認した
- [ ] 復元後、`personal-mcp event-list` で読み取れることを確認した
- [ ] 最新レコードのタイムスタンプが想定の範囲内であることを確認した

---

## MVP後の論点

- バックアップ後の追記分をどのように記録・回収するか
- 世代管理を行う場合の復元世代の選択基準
- 復元後の動作検証をどこまで自動化するか

これらは Phase 3 の論点として切り分ける。詳細は [`backup-mvp-options.md`](./backup-mvp-options.md) の「Phase 3 に送る論点」を参照。

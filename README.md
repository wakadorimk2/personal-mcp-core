# ふにゃ秘書たん

「どんな調子でも続けられる強さ」を育てる、自己コンディション観測ツール。

爆発的な頑張りよりも、波をならして続ける力のほうが長期では強い。このツールはその基盤になることを目指している。

---

## これは何か

生産性アプリでも、自己啓発ツールでもない。

あなたの状態を静かに記録して、**波をならす**ためのツール。

### 3つの原則

- **日次スナップショット** — 1日2〜3回の状態記録で十分。分単位の計測は不要。
- **不可逆ログ** — 書き換えない・削除しない。ただし表示は圧縮して軽く保つ。
- **評価しない** — スコアで赤くしない・落ち込ませない。「休んだ」も行動として記録する。

### ふにゃ秘書たんとは

観測者である。励まさない・評価しない・促さない。行動が起きたあとに、静かに事実を記録する。ユーザーを最適化しようとしない。ただ、横にいる。

---

## 体験

1. **観測** — アプリを開いて（または押して）、今の状態をひとこと記録する
2. **静かな記録** — 保存される。それだけ。
3. **事実通知（オプション）** — 行動が観測されたあとに限り、短く静かに通知する
   > 「開発の記録を残しました」「ゲームの活動を記録しました」
   >
   > 促さない・褒めない・煽らない
4. **日次振り返り** — その日のスナップショット一覧を眺める。分析ではなく、眺める。

---

## 何ができるか

### 現在（CLI、実装済み）

MVP の中核はすでに実装されている。現在は共通イベント基盤で記録し、PoE2 はその上の代表ユースケースとして扱っている。

```bash
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

イベントはデータディレクトリ内の `events.jsonl` に追記されます（削除・書き換えは不可）。既定保存先は `~/.local/share/personal-mcp/` です。`poe2-log-*` は互換用の入口で、保存先も共通イベントストアです。

---

## データモデル方針

イベントは共通 JSONL 形式（`<data-dir>/events.jsonl`）で表現する。追記のみ。編集・削除はしない。

### データ保存先

- ユーザーデータ（個人ログの正本）は **repo 外の `data-dir`** に保存する
- 保存先解決は `--data-dir` > `PERSONAL_MCP_DATA_DIR` > XDG 既定（`~/.local/share/personal-mcp/`）の順
- `repo/data/` は **開発・テスト・サンプル用途のみ**
- `repo/data/` に実ユーザーログ・バックアップ・復元成果物を置かない
- 詳細な運用ルールは [`docs/data-directory.md`](./docs/data-directory.md) を参照

### 最小イベント契約

| フィールド | 必須/推奨 | 説明 |
| --- | --- | --- |
| `ts` | 必須 | タイムスタンプ（ISO 8601 タイムゾーン付き）。内部保存は UTC を原則とする |
| `domain` | 必須 | ドメイン識別子（下記 MVP 許可リストを参照） |
| `payload.text` | 必須 | 記録本文 |
| `tags` | 必須 | タグリスト（空配列可） |
| `payload.meta.kind` | 推奨 | イベント種別（`note` / `session` / `milestone` など） |
| `payload.meta.source` | 推奨 | データ取得元（`"manual"` など） |
| `payload.meta.ref` | 推奨 | 参照先（Issue 番号など） |

`payload.meta` ごと省略できる（`poe2-watch` による自動記録など）。新しいトップレベルフィールドは追加しない。

Issue #79 では、目標契約として `v` / `kind` / `data` を持つ Event Contract v1 を別文書で定義している。現行保存形式はまだその契約に未準拠な legacy record なので、差分と対応方針は [docs/event-contract-v1.md](./docs/event-contract-v1.md) を参照。

### タイムスタンプ方針

- 内部保存は UTC を原則とする（実装の `_now_iso()` は `datetime.now(timezone.utc).isoformat()` を使用）
- ドキュメント上のイベント例は読みやすさのため JST（`+09:00`）で表記する
- 保存フォーマット自体はタイムゾーン付き ISO 8601 とし、既存レコードのオフセットはそのまま保持する

### MVP で明示サポートする domain

| domain | 説明 |
| --- | --- |
| `poe2` | Path of Exile 2 の活動記録 |
| `mood` | 気分・体調記録 |
| `general` | 分類不要なメモや雑記 |
| `eng` | エンジニアリング全般（調査・設計・学習など） |
| `worklog` | 作業記録・進捗ログ |

**domain 命名ルール：**

- ASCII 小文字
- 単数名詞または短いカテゴリ名
- 区切りは必要時のみ `_`
- `eng` は広いエンジニアリング活動（調査・設計・思考）、`worklog` は具体的な作業記録（セッション・進捗）として使い分ける

`event-add` で受け付ける domain は上記 allowlist のみとする。追加条件は [docs/domain-extension-policy.md](./docs/domain-extension-policy.md) を参照。

### eng / worklog の最小 kind セット

`payload.meta.kind` に設定する推奨値（`eng` / `worklog` 向け）：

| kind | 用途 |
| --- | --- |
| `note` | 調査メモ、気づき、短い記録 |
| `session` | 作業セッション、切り分け、実施ログ |
| `milestone` | 方針確定、区切り、到達点 |

### イベント例

#### eng / note

```json
{
  "ts": "2026-03-04T18:00:00+09:00",
  "domain": "eng",
  "payload": {
    "text": "MCP adapterの調査メモ",
    "meta": {
      "kind": "note",
      "source": "manual"
    }
  },
  "tags": ["research"]
}
```

#### worklog / session

```json
{
  "ts": "2026-03-04T19:00:00+09:00",
  "domain": "worklog",
  "payload": {
    "text": "Issue #23の切り分け",
    "meta": {
      "kind": "session",
      "ref": "#23"
    }
  },
  "tags": ["debug"]
}
```

#### eng / milestone

```json
{
  "ts": "2026-03-04T20:00:00+09:00",
  "domain": "eng",
  "payload": {
    "text": "JSONL append-only方針を確認",
    "meta": {
      "kind": "milestone"
    }
  },
  "tags": ["schema"]
}
```

#### worklog / note

```json
{
  "ts": "2026-03-04T21:00:00+09:00",
  "domain": "worklog",
  "payload": {
    "text": "レビュー前に再現手順を整理",
    "meta": {
      "kind": "note",
      "source": "manual"
    }
  },
  "tags": ["review"]
}
```

### 現在の実装

- 汎用 `event-add` / `event-list` / `event-today` がある
- `mood-add` は `domain="mood"` のイベントとして保存する
- `poe2-log-add` / `poe2-log-list` は `domain="poe2"` の専用入口として動く
- `poe2-watch` は `Client.txt` から `area_transition` を自動記録する

### 原則

- 追記のみ。編集・削除はしない。
- 既存 `poe2` / `mood` / `general` のレコード形式を壊さない。
- 自動取得を後から足すときも、同じイベント形式で追加する。

---

## Plan / Roadmap

**この README での MVP 達成の定義**

- 共通イベント追加 (`event-add`)
- 日次タイムライン一覧 (`event-list` / `event-today`)
- 気分記録 (`mood-add`)
- 単一保存先（`<data-dir>/events.jsonl`）
- 代表ユースケースとしての PoE2 記録 (`poe2-log-*` / `poe2-watch`)

### Now

- CLI ベースの観測フローは動いており、MVP の必須要素は揃っている
- 保存形式は `events.jsonl` に統一され、PoE2 も mood も同じイベント形式で追記される
- PoE2 では手動記録に加えて `Client.txt` 監視による自動記録も最小実装されている

### Next

- domain 拡張を README と CLI 例の両方で使いやすくする
- `eng` / `worklog` / `art` / `life` など、PoE2 以外の継続観測ユースケースを具体化する
- 表示面では複数ドメインを無理なく眺められるタイムライン整理を進める
- モバイルホーム画面や簡易 UI など、「記録を始めるまでの摩擦」を下げる入口を検討する

### Later

- ゲームログ以外の自動取得（Git コミット、外部サービス、各種ログ）を共通イベント形式に載せる
- ローカル中心のまま運用しやすくするためのインフラ化を進める
- 週次・月次の眺め、表示圧縮、必要最小限の通知などを実データに合わせて足す
- オプトイン前提の外部連携や集計は、ローカル運用の価値を損なわない範囲でのみ検討する

---

## プライバシー方針

- 個人の活動データはローカルに保存し、非公開。
- 集合統計・外部送信は明示オプトインのみ。
- 現状、外部送信機能はない。

---

## 互換性ポリシー（MVP期間中）

> 詳細・背景: [Issue #19](https://github.com/wakadorimk2/personal-mcp-core/issues/19)

### 保証するもの

- **JSONL イベント形式**（`<data-dir>/events.jsonl` のフィールド定義）
  - 破壊的変更を行う場合は `schema_version` フィールドを追加し、ワンタイム移行スクリプトを同伴する

### 保証しないもの

- CLI コマンド名・オプション
- 内部モジュール構造・import パス
- MCP アダプター IF
- 設定ファイル形式

### 破壊的変更の方針

- MVP 期間中はいつでも破壊的変更を行う可能性がある
- **恒久互換レイヤは持たない**
- データ形式を変更する場合は、ワンタイム移行スクリプトを同伴する（互換レイヤは残さない）
- 変更時はドキュメントを更新する

---

## 開発者向け

```bash
# 開発用インストール（ruff + pytest を含む）
pip install -e ".[dev]"

# コードチェック
ruff check .

# 自動修正
ruff check . --fix

# フォーマット
ruff format .

# テスト
pytest

# エントリーポイント動作確認
python -m personal_mcp.server poe2-log-list --n 5

# AI_GUIDE.md の同期確認
diff AI_GUIDE.md src/personal_mcp/AI_GUIDE.md
```

**構成：**

```
src/personal_mcp/
├── server.py               # CLIエントリーポイント
├── tools/event.py          # 共通イベント記録・一覧
├── tools/poe2_client_watcher.py  # PoE2 Client.txt 監視
├── storage/jsonl.py        # 追記型JSONLストレージ
├── adapters/mcp_server.py  # MCP system context adapter
└── core/guide.py           # AI_GUIDE.md ローダー
```

**貢献の歓迎範囲：**

- バグ修正・型エラー修正
- テストの追加・改善
- ドキュメントの改善

機能追加は事前にIssueで議論してください。

---

## ライセンス

未定。個人利用を主軸に方針検討中。決まったら更新します。

# Issue #79 Proposal Review

Issue #79 の Event Contract v1 提案について、現行実装との差分と論点をレビューしやすい形で整理したメモ。

この文書は実装仕様の確定ではなく、提案レビューのための論点整理を目的とする。

## 結論

Issue #79 が提案する Event Contract v1（`data`・トップレベル `kind` / `source` / `ref`・`v` 必須）は、現行実装（`payload`・`payload.meta.*`・`v` なし）と複数の互換ギャップがある。

docs issue として文書だけ先に固定すること自体は可能だが、「現行コードはまだ v1 ではない」ことを同じ文書内で明示しないと、後続の実装や reader 設計で誤読を生みやすい。

最もバランスがよいのは、Issue #79 の v1 定義を採用しつつ、現行実装との乖離を同じドキュメント内にマッピングとして併記する案。

## 選択肢比較

| option | pros | cons | prerequisites |
|---|---|---|---|
| A. 現状実装をそのまま v1 として docs 化する | 実装と文書が即座に一致する。追加実装なしで整合が取れる。 | Issue #79 が意図している `data` / トップレベル `kind` / `v` の整理を捨てることになる。`payload.meta` が省略可能な現仕様のままだと `kind` を最低契約にしづらい。 | なし |
| B. Issue #79 の理想形をそのまま v1 として docs に定義する | Acceptance Criteria に沿いやすい。将来の domain 拡張や reader-first の説明がしやすい。 | 文書制定時点で実装・README・テストが旧形式を前提にしており、文書とコードの乖離が大きい。 | docs 先行を許容する判断 |
| C. Issue #79 の v1 を docs に定義しつつ、現行実装との乖離マッピングを併記する | v1 の目標形を保ちつつ、今どこが未追従かを明示できる。後続 issue を切りやすい。 | 文書量は少し増える。現行実装が v1 非準拠であることを明記する必要がある。 | なし |
| D. v1 文書化と同時に実装も移行する | 文書と実装が一致する最も clean な状態になる。 | Issue #79 の out of scope を超える。既存 JSONL への移行方針も必要になる。 | 別 issue で移行設計を先に整理すること |

## 推奨案

推奨案は Option C。

Issue #79 の `data` / トップレベル `kind` / `v` という方向性は、将来の domain 拡張と reader-first 互換性の説明に一貫性がある。一方で、現行実装は `payload.text` と `payload.meta.kind` に強く依存しており、docs だけを先に固定するなら、その差分を同じ文書内に明示した方が安全。

## 現行実装との主なギャップ

| gap | 現行 | Issue #79 提案 | 影響 |
|---|---|---|---|
| payload 名称 | `payload` | `data` | record 形状が変わるため breaking |
| kind の位置 | `payload.meta.kind` | トップレベル `kind` | reader / filter / tests が壊れるため breaking |
| source の位置 | `payload.meta.source` | トップレベル `source` | writer / examples / docs 更新が必要 |
| ref の位置 | `payload.meta.ref` | トップレベル `ref` | writer / examples / docs 更新が必要 |
| version | `v` なし | `v: 1` 必須 | 新規 reader では必要になるが、旧 reader が unknown top-level key を無視する限り追加自体は読み取り上 non-breaking と整理可能 |
| tags の扱い | 必須（空配列可） | 任意トップレベル | 現行 README と `Event` 定義では必須前提。契約差分の明示が必要 |
| 本文の所在 | `payload.text` 前提 | `data.text` は examples にあるが必須とは未確定 | generic reader の表示仕様が宙に浮く |

## 重要論点

### 1. `v` は「field 追加」と「契約準拠」を分けて書くべき

`v` の追加自体は、旧 reader が unknown top-level key を無視できるなら、読み取り互換の観点では non-breaking と説明できる。

ただし、Issue #79 のように `v` を required key とするなら、既存レコードは v1 準拠ではない。ここを混ぜると「non-breaking なのに既存レコードは不適合」という一見矛盾した説明になるため、文書では分けて書く方がよい。

### 2. `tags` の required / optional は明示的に決める必要がある

現行 README では `tags` は必須で空配列可とされている。一方、Issue #79 は `tags` を任意トップレベルとして扱っている。

この変更は `kind` や `data` ほど大きく見えにくいが、最低契約を定義する文書では重要な差分になる。

### 3. generic reader が `text` をどう扱うかを曖昧にしない方がよい

現行 CLI と表示ロジックは `payload.text` を本文の所在として前提にしている。Issue #79 では examples に `data.text` が出てくるが、`data` の内部構造を完全標準化しない前提なので、`text` を最低限の慣例として残すのか、generic reader は本文表示を契約に含めないのかを決めないと後続実装がぶれやすい。

## Next Action

- [ ] `docs/event-contract-v1.md` を新規作成し、Issue #79 の Event Contract v1 定義を文書として固定する
- [ ] 同ドキュメントに「現行実装との乖離」セクションを追加し、少なくとも `payload` / `kind` / `source` / `ref` / `v` / `tags` / `text` の差分を列挙する
- [ ] `v` については「旧 reader にとっての field 追加」と「既存レコードの v1 準拠性」を分けて説明する
- [ ] `tags` を required のままにするか optional にするかを本文で明記する
- [ ] generic reader のために `data.text` を最低限の慣例として残すかどうかを本文で明記する
- [ ] 後続 issue として、実装移行、既存 JSONL の migration 方針、reader tolerance 検証を分離して起票する

## リスク / 不確実性

- docs 先行で実装未対応の期間が長いと、文書を信じて新規コードを書いた人が旧形式データで破綻する可能性がある
- `data.text` を契約に含めない場合、generic reader の表示仕様を別途定義しないと利用者体験が不安定になる
- `tags` の required / optional を曖昧にすると、最低契約の説明が揺れる

## 参照根拠

- `gh issue view 79 --repo wakadorimk2/personal-mcp-core`: Issue #79 の提案内容
- [README.md](/tmp/personal-mcp-core-issue79-review/README.md#L80): 現行の最小イベント契約
- [docs/architecture.md](/tmp/personal-mcp-core-issue79-review/docs/architecture.md#L114): 現行 Event schema と `payload.meta.kind` の説明
- [src/personal_mcp/core/event.py](/tmp/personal-mcp-core-issue79-review/src/personal_mcp/core/event.py#L11): `Event` dataclass の定義
- [src/personal_mcp/tools/event.py](/tmp/personal-mcp-core-issue79-review/src/personal_mcp/tools/event.py#L31): `event_add()` の record 構築
- [src/personal_mcp/server.py](/tmp/personal-mcp-core-issue79-review/src/personal_mcp/server.py#L24): 表示系が `payload.text` を参照していること
- [src/personal_mcp/server.py](/tmp/personal-mcp-core-issue79-review/src/personal_mcp/server.py#L206): `poe2-log-list` が `payload.meta.kind` を参照していること
- [src/personal_mcp/tools/poe2_client_watcher.py](/tmp/personal-mcp-core-issue79-review/src/personal_mcp/tools/poe2_client_watcher.py#L54): watcher が `meta.kind` / `meta.source` を書いていること
- [tests/test_event.py](/tmp/personal-mcp-core-issue79-review/tests/test_event.py#L39): `payload.text` 前提のテスト
- [tests/test_poe2.py](/tmp/personal-mcp-core-issue79-review/tests/test_poe2.py#L38): `payload.meta.kind` 前提のテスト

## PR 用要約

Issue #79 の Event Contract v1 提案について、現行実装との差分がレビューしやすい形で分かるよう論点整理を追加した。

特に、`payload -> data`、`payload.meta.kind -> top-level kind`、`v` の required 化に加えて、`tags` の required / optional 差分と、generic reader が依存している `payload.text` の扱いを明示した。

推奨案は、v1 の目標形を docs で定義しつつ、現行実装との乖離マッピングを同じ文書に併記する案。

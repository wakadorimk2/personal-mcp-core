# domain 拡張ポリシー

> スコープ: `personal-mcp-core` における domain 追加の最小ポリシーと allowlist 追加条件
> 関連 Issue: #77

## 目的

この文書は、新しい `domain` を追加する前に満たすべき最小条件を定義する gate 文書である。
個別 domain の仕様を決めるものではなく、domain 契約 docs の記載要件と allowlist 追加条件を固定する。

## この文書と Issue の関係

- #77 は domain 拡張ポリシーと allowlist 追加条件を定義する
- #70-#78 相当の個別 domain 契約 docs は、この文書のチェックリストに従って記述する
- #80 は別 Issue であり、この文書の成立条件ではない

この文書は #80 をブロッカーとしない。#80 が未着手でも、domain 拡張の gate 文書として独立して成立する。

## 1. domain を増やしてよい条件

新しい domain を提案するには、以下をすべて満たすこと。

### 1.1 責務の非重複

- 既存 domain と責務が重複しないこと
- `general` で十分に表現できる記録のために新 domain を作らないこと
- 既存 domain と何が違うかを 1-2 文で説明できること

### 1.2 命名規則

- ASCII 小文字を使うこと
- 単数名詞または短いカテゴリ名を優先すること
- 区切り文字は必要な場合のみ `_` を使うこと
- 既存 domain と紛らわしい名前を避けること

### 1.3 最小イベント例

- 実際の利用を想定した JSONL 例を最低 1 件示すこと
- 最低限 `ts` / `domain` / `payload.text` / `tags` を含むこと
- 新しいトップレベルフィールドを追加しないこと

例:

```json
{
  "ts": "2026-03-04T18:00:00+09:00",
  "domain": "general",
  "payload": {
    "text": "新 domain 追加ポリシーを確認"
  },
  "tags": ["schema"]
}
```

### 1.4 互換性

- 共通イベント形式は `ts` / `domain` / `payload` / `tags` に閉じること
- 既存レコードの解釈を壊す前提を持ち込まないこと
- domain 固有情報は `payload` 配下に閉じること
- 詳細な互換性方針は [`README.md`](../README.md) の「互換性ポリシー（MVP期間中）」を参照すること

### 1.5 秘匿リスク

- 提案する domain が個人情報、健康情報、金融情報、認証情報、業務上の秘匿情報などを含みうるかを確認すること
- センシティブ domain は、allowlist 追加前に秘匿ルールを定義する別 Issue を先に通すこと
- 契約 doc には privacy / secret / sensitive 情報の扱いを必ず明記すること

### 1.6 テスト観点

- allowlist をコードに追加する場合は、その変更をカバーする最小テストを追加すること
- docs のみを追加する段階では、新規テストは必須ではない
- 既存テストを壊さないこと

## 2. domain 契約ドキュメントの必須項目

新しい domain の契約 doc には、少なくとも次を含めること。

- [ ] その domain の責務と境界
- [ ] 既存 domain と重複しない理由
- [ ] 代表イベント例
- [ ] 必須/任意フィールドの扱い
- [ ] 既存 schema との整合
- [ ] privacy / secret / sensitive 情報の扱い
- [ ] allowlist 追加前提の検証項目
- [ ] 必要なテスト観点
- [ ] 互換性に関する注意
- [ ] 依存する別 Issue がある場合の扱い

契約 doc の配置場所は repo の既存 docs 構造に合わせる。新しい専用ディレクトリを必須とはしない。

## 3. allowlist に追加する条件

### 原則

契約 docs が先、allowlist 反映は後とする。契約 doc がない状態で allowlist を更新しない。

### 必須の変更セット

| 変更 | 要否 | 備考 |
| --- | --- | --- |
| domain 契約 doc の追加/更新 | 必須 | セクション 2 の項目を満たす |
| README の導線更新 | 必須 | allowlist の説明または関連 docs から辿れる状態にする |
| allowlist のコード更新 | コード変更時必須 | 正本は `src/personal_mcp/core/event.py` の `ALLOWED_DOMAINS` |
| テスト追加/更新 | コード変更時必須 | 例: `tests/test_event.py`, `tests/test_cli.py` |

### 手順

1. domain 契約 doc を作成し、レビュー可能な状態にする
2. センシティブ domain の場合は、秘匿ルール Issue を先に定義して承認を得る
3. 契約 doc のレビュー完了後に allowlist を更新する
4. 必要なテストを追加し、既存テストを壊していないことを確認する

## 4. kind に関する注記

kind が導入されている場合、各 domain 契約は可能な範囲で kind を付与する。kind の定義は kind taxonomy v1（Issue #80）に従う

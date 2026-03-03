---
name: research-propose-structured
description: 調査・比較・提案を“結論先出し”で構造化して返す。実装はしない（コードは疑似コードまで）。
argument-hint: "[topic-or-constraints-or-issue-url]"
disable-model-invocation: true
---

# research-propose-structured

## Mission
調査・提案タスクを「構造化された結論」で返し、実装タスクと混ざらないようにする。
入力は `$ARGUMENTS`（テーマ/制約/URL/issue番号のいずれか）。必要ならまず issue / ドキュメントを読んでから整理する。

## Rules（絶対）
- 実装しない（ファイル変更・PR作成もしない）
- コードを書かない（必要な場合は疑似コードまで）
- 参照した根拠（リンクやファイル）を必ず列挙する
- 「やるべき」の断定を避ける（選択肢整理＋推奨“案”として提示）
- 不確実な点は“不確実性”として明記し、推定と事実を混ぜない

## Inputs（受け取り方）
- `$ARGUMENTS` に含まれる情報だけで開始する
- 足りない情報がある場合は、質問で止めずに「仮定/未確定」として明記し、条件付きで提案する
  - ただし結論が大きく変わる前提（例: 予算が0か、セキュリティ要件が厳格か等）は“不確実性”に上げる

## Output（必ずこの順・この見出しで出力）
### 1. 結論（1〜3行）
- <結論>

### 2. 選択肢比較
| option | pros | cons | prerequisites |
|---|---|---|---|
| A |  |  |  |
| B |  |  |  |

### 3. 推奨案と理由（2〜4行）
- <推奨案（案）>: <理由>

### 4. 具体 Next Actions（gh issue 化できる粒度）
- [ ] <action A>
- [ ] <action B>

### 5. リスク / 不確実性
- <risk X>: <impact> / <mitigation>
- <uncertainty Y>: <why uncertain> / <how to validate>

### 6. 参照根拠
- <file or URL>: <why referenced>

## Invocation Examples
- `/research-propose-structured "Compare approaches to add a new adapter (constraints: low effort, reversible, python)"`
- `/research-propose-structured 25`
- `/research-propose-structured https://github.com/wakadorimk2/personal-mcp-core/issues/25`
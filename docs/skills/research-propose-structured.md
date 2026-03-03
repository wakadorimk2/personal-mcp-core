# research-propose-structured

**種類**: research
**正本**: このファイル（`docs/skills/research-propose-structured.md`）
**Claude用アダプタ**: `.claude/skills/research-propose-structured/SKILL.md`

---

## Mission

調査・提案タスクを「構造化された結論」で返し、実装タスクと混ざらないようにする。

---

## Rules（絶対）

- 実装しない（ファイル変更・PR 作成もしない）
- コードを書かない（必要な場合は疑似コードまで）
- 参照した根拠（リンクやファイル）を必ず列挙する
- "やるべき" の断定を避ける（選択肢整理＋推奨"案"として提示）
- 不確実な点は "不確実性" として明記し、推定と事実を混ぜない

---

## Inputs

- 調査テーマ / 制約 / URL / issue番号
- 足りない情報は「仮定/未確定」として明記し、条件付きで提案する
  - ただし結論が大きく変わる前提は "不確実性" に上げる

---

## Output テンプレ（この順・この見出しで出す）

### 1. 結論（1〜3行）
- \<結論\>

### 2. 選択肢比較
| option | pros | cons | prerequisites |
|---|---|---|---|
| A | | | |
| B | | | |

### 3. 推奨案と理由（2〜4行）
- \<推奨案（案）\>: \<理由\>

### 4. Next Action（gh issue 化できる粒度）
- [ ] \<action A\>
- [ ] \<action B\>

### 5. リスク / 不確実性
- \<risk\>: \<impact\> / \<mitigation\>
- \<uncertainty\>: \<why uncertain\> / \<how to validate\>

### 6. 参照根拠
- \<file or URL\>: \<why referenced\>

---

## 禁止

- ファイル変更・PR 作成
- 断定的な推奨（"すべき" 表現）
- 実装コードの記述（疑似コードを超えるもの）

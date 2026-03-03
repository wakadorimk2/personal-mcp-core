---
name: implement-issue-minimal
description: GitHub Issueをスコープ厳守で実装し、最小テストまで回して、diffとコミット案までを一括で出す。実装依頼のときに使う（自動実行はしない）。
argument-hint: "[issue-url-or-number]"
disable-model-invocation: true
---

# implement-issue-minimal

## Mission
与えられた Issue を **Scope 内だけ**で実装し、最小テストを実行し、最終的に **diff + 実行コマンド結果 + コミット案** を提示する。

入力は `$ARGUMENTS`（issue番号またはURL）。まず `gh issue view` などで本文（Goal/Scope/完了条件）を取得してから進める。

## Rules（絶対）
- 仕様の追加提案をしない（改善案は“別issue候補”として最後に1行だけ、または出さない）
- Scope外を実装しない（リファクタ/整理も禁止。issueに明示がある場合のみ）
- 「足りない情報」は質問で止めず、**仮定**として明記して進める。ただし破壊的変更になり得る場合は中断して理由を述べる
- 1 issue = 1 PR を想定し、変更は最小限にする

## Procedure（作業手順）
1) Issueを読む  
   - `$ARGUMENTS` を使い Issue本文を取得し、Goal/Scope/完了条件を短くメモする

2) 実装方針（3〜5行）  
   - 変更の核心 / 影響範囲 / 不採用案（あれば1行）だけ

3) 変更を実施  
   - 必要なファイルを `Read/Grep/Glob` で特定し、最小の編集で実装する  
   - Scope外のファイルには触れない

4) 最小テスト/検証  
   - 可能なら `pytest -q` など最小コマンドを実行し、結果を短く記録する  
   - テストが存在しない場合は「実行できない理由」を明記し、代替の軽量チェック（lint/実行例など）を行う（Scopeに反しない範囲）

5) 出力を整える（この順で出す）
   1. 実装方針（箇条書き 3〜5行）
   2. 変更ファイル一覧（ファイル / 変更種別 / 理由）
   3. 実行コマンドと結果（コピペ可能な形）
   4. 仮定（あれば）
   5. 完了チェックリスト
   6. `git diff`（または差分要約）とコミットメッセージ案（Conventional Commits）

## Output Templates

### 1) 実装方針
- <変更の核心>
- <影響範囲>
- <不採用案（あれば）>

### 2) 変更ファイル一覧
| file | type (add/edit/del) | reason |
|---|---|---|

### 3) 実行コマンド
```bash
# commands you ran
````

### 4) 仮定

* <前提A>
* <前提B>

### 5) 完了チェック

* [ ] Scope内のみ
* [ ] 破壊的変更なし（仮定は明記）
* [ ] テスト/検証を実行し結果を記録
* [ ] コミット案が規約に沿う

## Invocation Examples

* `/implement-issue-minimal 25`
* `/implement-issue-minimal https://github.com/wakadorimk2/personal-mcp-core/issues/25`

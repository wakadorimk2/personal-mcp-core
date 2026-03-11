# eng domain concept / contract

> Scope: `eng` domain を Human Observability 上でどう扱うかの concept / contract を固定する。
> Related: #193 (concept), #204 (ingest responsibility spec), #247 (GitHub ingest MVP)

## 1. Goal

`eng` domain は、開発活動を「成果物の数」ではなく、
**判断・探索・実装の状態変化**として観測するための domain である。

この文書は concept / boundary を固定する。
取り込み実装の責務、保存経路、CLI 導線、完了条件は扱わない。

## 2. Responsibility

`eng` domain が扱うのは、少なくとも次の 4 区分で説明できる開発活動である。

- Issue / PR の開始、更新、完了
- 実装作業の開始、切り替え、完了
- 設計・調査・実験の記録
- 判断・方針変更・不確実性の記録

中心に置くのは「何を作ったか」だけでなく、
「どう判断したか / どこで迷ったか / 何が変わったか」である。

## 3. In / Out

### In

- GitHub Issue / PR / commit に由来する開発活動
- 手動で残す設計メモ、調査メモ、実装判断ログ
- 実装中に発生した block / uncertainty / decision の記録
- 後から付与する annotation の対象となる eng event

### Out

- GitHub ingest 実装の対象種別、除外条件、dedup、storage 完了条件
- 時間計測や工数報告そのものを主目的とする記録
- 良し悪し、生産性評価、優先度評価などの interpretation
- secret / credential / private business information を含む内容

## 4. Domain boundary

### 4.1 `general` との境界

- `general` は分類不要な雑記・日常メモに使う
- `eng` は開発活動としての文脈が明示できる記録に使う
- 「既存 domain と何が違うか」を 1-2 文で言えない場合は `general` を優先する

### 4.2 `worklog` との境界

- `worklog` は進捗・作業実施ログ・時系列の業務記録を置く
- `eng` は設計判断、探索、実装の状態変化、技術的節目を置く
- 同じ作業でも「何をしたか」を時系列に残すなら `worklog`、
  「技術的に何が変わったか」を残すなら `eng`

### 4.3 GitHub 起点ログとの境界

- `eng` domain は GitHub を domain として扱わない
- GitHub は eng event を生成する 1 つの source である
- 手動ログ、`github_sync`、`github_ingest` は同じ `eng` domain へ流入しうるが、
  それぞれの実装責務は concept ではなく別 issue / doc で管理する

## 5. 3-layer mapping

| layer | eng で扱うもの | 含めないもの |
|---|---|---|
| Event | Issue/PR/commit、設計メモ、実装開始/完了、判断の事実 | 評価、感情ラベル、良し悪し判定 |
| Annotation | 後付けの補足、背景、blocker、uncertainty | 元 event の書き換え |
| Interpretation | phase 推定、ボトルネック把握、負荷や偏りの読解 | Event schema への介入 |

MVP では `annotation` / `interpretation` の実装責務は
[`docs/mvp-contract-decisions.md`](./mvp-contract-decisions.md) に従う。
`eng` concept は 3 層の意味を定義するが、実装方式までは固定しない。

## 6. Event examples (non-binding)

- issue_created
- issue_triaged
- pr_opened
- implementation_started
- implementation_finished
- design_conflict
- experiment_started
- experiment_result

上記は concept 確認用の例であり、`kind` / `source` / `ref` / `data.*` の実装仕様は
[`docs/eng-ingest-impl.md`](./eng-ingest-impl.md) を参照する。

## 7. Privacy / secret handling

- repository private 情報、credential、token、顧客情報、業務上の秘匿情報は event text や `data.*` に入れない
- GitHub 由来 event でも、保存対象は Human Observability に必要な最小情報に留める
- 秘匿ルールの追加が必要な場合は、`eng` concept ではなく別 issue で扱う

## 8. Compatibility

- `eng` event は Event Contract v1 に従う
- domain 固有情報は `data` 配下に閉じる
- `kind` は cross-domain taxonomy を使い、`eng` 固有 kind は導入しない

## 9. Related references

- [`docs/design-principles.md`](./design-principles.md): Human Observability と 3 層構造の原則
- [`docs/mvp-contract-decisions.md`](./mvp-contract-decisions.md): annotation / interpretation / source-ref の MVP 決定
- [`docs/eng-ingest-impl.md`](./eng-ingest-impl.md): GitHub ingest の実装責務と受け入れ条件
- [`docs/domain-extension-policy.md`](./domain-extension-policy.md): domain contract doc の必須項目

## 10. Future considerations

- `eng` を将来 `dev` / `research` に分割する必要があるか
- GitHub 以外の開発ログ source をどこまで `eng` に含めるか
- interpretation をどの粒度まで自動生成するか

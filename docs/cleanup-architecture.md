# Cleanup Architecture — Taxonomy and Constitution

> スコープ: cleanup を単発作業ではなく、継続運用できる architecture として定義する
> 親 Issue: #259
> 関連: #94, #258, #260, #263, #264
> 更新日: 2026-03-10
>
> **この文書は設計記録であり、cleanup pipeline や scheduler の実装導入は後続 Issue へ分離する。**
> 実行面の設計は [`docs/cleanup-pipeline.md`](./cleanup-pipeline.md) を参照する。

---

## Goal

`personal-mcp-core` における cleanup を、
「何を drift / entropy / garbage とみなすか」
「どこまで自動修正してよいか」
「どこで review に止めるか」
の 3 点で再現可能にする。

この文書では次を扱う。

- cleanup taxonomy の定義
- category ごとの trigger / input / expected output / automation ceiling の整理
- cleanup constitution としての auto-fix 境界、停止条件、証跡要件の定義
- cleanup と仕様変更を分ける判断基準の明文化

## Non-goal

- cleanup の実行自動化そのもの
- docs / code / project metadata の一括修正
- CI や scheduler への組み込み
- structural constraints や doc drift detector の実装詳細確定

## 1. Terms

### Entropy

repo 内に残った差分や記述のずれのうち、
**意味の追加ではなく、理解コストや判断ノイズを増やすもの** を指す。

例:

- 正本と README の表記ずれ
- 現在の構造と合わない古い導線
- 同じルールを別の言い方で重複記述した docs

### Garbage

entropy のうち、
**削除・隔離・差し替えで減らせる残留物** を指す。

例:

- 参照されない古い説明
- obsolete な例やテンプレ
- 正本と矛盾する補助文書

補足:

- entropy は「ずれ」の総称
- garbage はその中でも cleanup action の対象にしやすいもの
- 仕様差分や新しい設計判断は cleanup ではなく change として扱う

## 2. Automation Levels

cleanup は category ごとに次の automation level を上限として扱う。

| level | name | meaning |
|---|---|---|
| L0 | detect only | drift を検出して記録するだけ。修正しない |
| L1 | propose only | 修正案や Issue/PR draft を作るが、本文やファイルは確定しない |
| L2 | bounded auto-fix | 正本が明確な範囲に限り、局所・可逆・非仕様変更の修正を行う |
| L3 | review required | 変更可否は人間 review で決める。自動適用しない |

注記:

- `L2` は「完全自律」を意味しない
- 1 つの cleanup flow で detect は自動でも、apply は `L3` ということがありうる

## 3. Cleanup Taxonomy

| category | main trigger | main input | expected output | automation ceiling |
|---|---|---|---|---|
| micro cleanup | 実作業中に局所 drift を発見したとき | 現在の diff、近傍ファイル、正本 docs、既存テスト | 小さい cleanup patch、または follow-up Issue 1 件 | `L2` |
| periodic cleanup | 定期棚卸しや drift 蓄積の見直し時 | repo inventory、stale docs、unused path、近接 Issue 群 | scope を絞った cleanup plan / Issue / PR | `L3` |
| doc drift detection | 正本 docs と導線 docs / 実装の不一致疑い | contract docs、README、AI guide、実装参照 | mismatch list と「cleanup か spec change か」の判定 | detect は `L0`、apply は `L2` まで |

### 3.1 Micro cleanup

位置づけ:

- 実装や docs 作業の近傍で見つかる、小さく閉じた drift を扱う
- 単独の cleanup task にも、別 task 中の付随 cleanup にもなりうる

典型例:

- typo、リンク先、見出し、表記ゆれの修正
- 既存正本に合わせた README の同期
- `#94` のような terminology cleanup

境界:

- 触っている範囲の近傍に閉じること
- 仕様意味を変えないこと
- 変更理由を 1 文で説明できること

### 3.2 Periodic cleanup

位置づけ:

- repo を時間単位で棚卸しし、局所では回収しきれない drift を整理する
- cleanup を「気合いの一掃」ではなく、定期的な inventory と分割実行に落とす

典型例:

- stale docs / stale scripts の棚卸し
- README / runbook / skills / policy の責務重複の見直し
- 大きな cleanup を child Issue に分割する前処理

境界:

- 先に inventory と分割方針を作る
- 一括修正より、分類と優先順位付けを先に行う
- 実修正は別 PR に分離してよい

### 3.3 Doc drift detection

位置づけ:

- docs と実態の不一致を継続的に見つける detection category
- cleanup 実行そのものではなく、cleanup / spec change の振り分け入力を作る
- signal 分解、detector 候補、triage 詳細は [`docs/doc-drift-detection.md`](./doc-drift-detection.md) を参照する

典型例:

- README と canonical doc の文言差
- policy 正本と導線の矛盾
- 実装済み/未実装の説明ずれ

境界:

- 検出結果だけでは cleanup と断定しない
- 「正本が何か」を固定できた場合に限り、同期修正へ進める

## 4. Constitution

### 4.1 Auto-fix してよい条件

次をすべて満たす場合に限り、cleanup を `L2` で auto-fix してよい。

1. 正本が 1 つに定まっている
2. 変更が仕様意味、挙動、契約、運用責務を変えない
3. 変更範囲が局所で、diff を人間が短時間で review できる
4. 変更理由を「既存正本への同期」で説明できる
5. 削除や置換が可逆で、失敗時に戻しやすい

許可例:

- typo / broken link 修正
- README を canonical doc に同期
- obsolete な補助説明を、正本参照へ置換

### 4.2 停止して review に回す条件

次のいずれかに当たる場合、cleanup は止めて review に回す。

- 正本候補が複数あり、どれに合わせるべきか曖昧
- 変更が仕様変更、責務変更、依存方向変更を含む
- 実装変更、migration、互換性判断が必要
- 削除対象が本当に不要かを機械的に確定できない
- diff が広範囲で、inventory と分割なしでは監査不能
- cleanup の名目で新しい設計判断を入れたくなっている

### 4.3 Cleanup の優先順

cleanup は次の順で扱う。

1. detect: drift を観測して分類する
2. classify: taxonomy category と automation level を決める
3. decide: cleanup か spec change かを判定する
4. execute: 許可範囲なら修正し、そうでなければ Issue / review に送る
5. record: 何を見て何を変えなかったかを残す

## 5. Cleanup と仕様変更を分ける判断基準

### cleanup とみなしてよいもの

- 既存正本に表記や導線を合わせるだけの変更
- obsolete / duplicate / contradictory な記述の削除や統合
- 現在の実装・契約をより正確に記述し直す変更

### cleanup ではなく spec change とみなすもの

- source of truth 自体を書き換える変更
- contract、責務境界、許可/禁止ルールを追加・変更する変更
- 実装の振る舞い、データ形式、migration 要否に影響する変更
- 「今まで曖昧だったので今回決める」という新規判断

### 実務上の判定ルール

次の問いに 1 つでも `yes` なら、cleanup ではなく spec change として扱う。

- この diff は repo の意味や約束を変えるか
- この diff がないと実装変更の説明が成立しないか
- どちらが正本かを人間判断なしに決められないか

## 6. Required Evidence for Cleanup Issue / PR

cleanup Issue / PR には最低限次を残す。

| field | required content |
|---|---|
| trigger | 何の drift をきっかけにしたか |
| category | micro cleanup / periodic cleanup / doc drift detection のどれか |
| source of truth | 何に同期したか |
| decision | cleanup と判定した理由、または spec change へ分離した理由 |
| scope | 今回直す範囲と、直さない範囲 |
| automation level | detect / propose / bounded auto-fix / review required のどこまで行ったか |
| evidence | diff、inventory、mismatch list、参照 Issue など |

PR では追加で次を明記する。

- 仕様変更を含んでいないこと、または含むので別 Issue 扱いにしたこと
- 削除・置換した対象の根拠
- 残件や follow-up の有無

## 7. Positioning with Nearby Work

- `#94` は terminology cleanup の既存例として、micro cleanup に位置づける
- `#258` は docs / policy の責務整理であり、cleanup constitution の source of truth 候補を整える近接作業
- `#260` は deterministic toolchain baseline であり、cleanup taxonomy とは分離して扱う
- structural drift の hard fail / advisory 設計は別 Issue で扱い、この文書では cleanup architecture 側の判断基準のみを定義する

## 8. Summary

cleanup は「雑にきれいにする作業」ではなく、
drift を分類し、正本との距離を測り、
auto-fix 境界と停止条件を固定したうえで扱う運用である。

この文書で固定したのは次の 5 点である。

- cleanup taxonomy は `micro cleanup` / `periodic cleanup` / `doc drift detection`
- 自動化は `L0-L3` の bounded model で扱う
- auto-fix は「正本が明確で、非仕様変更で、局所 diff」の場合に限る
- cleanup と spec change は「意味や約束を変えるか」で分ける
- 実行面と記録面は [`docs/cleanup-pipeline.md`](./cleanup-pipeline.md) で別管理する

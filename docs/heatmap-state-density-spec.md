# Heatmap State Change Density Spec

> **スコープ注記**
> この文書は Issue #253 の repo 内 authoritative spec である。
> heatmap が何を表すかという意味定義を固定し、後続の実装 Issue が参照できる状態を作る。
> 本文書は runtime 実装の完了を意味しない。現行の `/api/heatmap` は MVP として raw event count を返しており、
> 本文書に沿った集計・UI 導線への反映は follow-up Issue で行う。

## 1. Purpose

heatmap は raw event count をそのまま見せる UI ではなく、
一定時間におけるユーザーの state change density を可視化する UI として扱う。

この定義により、現状の違和感を見た目調整の問題ではなく、
可視化指標の意味定義の問題として整理する。

## 2. Design Premise

- 人生は「時間を状態変化に変換するプロセス」とみなす
- state change は観測解像度に依存する
- heatmap は単一固定指標を表示するものではなく、観測解像度によって見え方が変わる前提を持つ
- 将来の UI は解像度を切り替えられる前提を持つが、具体的な操作方式はこの文書では確定しない

## 3. Observation Layers

### 3.1 Coarse life view

粗い解像度では、意味のある life activity の集約を観測対象とする。

例:
- memo
- GitHub
- Steam
- illustration

ここでの heatmap は「その日にどれだけ人生上の意味ある活動変化があったか」を見るためのものとする。

### 3.2 Medium domain view

中粒度では、domain activity を観測対象とする。

例:
- writing
- coding
- gaming
- drawing

ここでは coarse life view より細かいが、raw event そのものではない activity 単位の変化を見る。

### 3.3 Fine event view

細粒度では raw event を観測対象にできる。
ただし、この view は coarse / medium よりも観測装置やイベント分割の影響を強く受ける。

## 4. Telemetry Position

telemetry は削除対象ではないが、人生そのものではなく観測装置側のイベントである。
そのため、通常の life view とは別レイヤーの観測として扱う。

原則:
- life view の主目的は、ユーザーの life activity における state change density の観測である
- telemetry view の主目的は、UI / instrumentation / debug の観測である
- telemetry を coarse life view の primary meaning として扱わない

## 5. Aggregation Unit

件数 vs 文字数を universal metric の二択として固定しない。
集約単位は、解像度や event kind に応じて自然なものを選ぶ。

例:
- coarse life view では activity cluster の有無や密度が自然な単位になりうる
- medium domain view では domain 別 activity のまとまりが自然な単位になりうる
- fine event view では raw event count が自然な単位になりうる
- memo 系では text length や note density が補助指標になりうる

このため、heatmap 全体に対して 1 つの universal metric を固定する前提は採らない。

## 6. Current Runtime vs Spec

現行 runtime の `/api/heatmap` は、`summary` を除くイベントを日単位に数えた `count` を返す。
これは MVP の暫定実装であり、本 spec の最終意味定義をまだ満たしていない。

後続 Issue は少なくとも以下を再議論せず参照できること:
- heatmap は state change density を表す
- coarse / medium / fine の観測解像度を前提とする
- telemetry は life view と別レイヤーで扱う
- 集約単位は単一固定ではなく、解像度依存で選ぶ

## 7. Non-goal

- この文書だけで heatmap 集計ロジックを確定実装すること
- ピンチ / スライダー / トグルの具体的な UI 操作を確定すること
- event taxonomy 全体を再設計すること
- telemetry 収集を廃止すること

## 8. References

- Parent issue: #252
- Decision record: #253
- Current heatmap runtime: `src/personal_mcp/tools/daily_summary.py`
- Current heatmap API surface: `src/personal_mcp/adapters/http_server.py`

# Import / Layering / Dependency Constraints — Issue #262

> スコープ: `src/personal_mcp/` の runtime module に対する structural constraint の設計
> 前提: current deterministic baseline は `pytest`, `ruff check .`, `ruff format --check .`,
> `guide-check` とし、repo tooling (`Makefile`, `pyproject.toml`) および
> [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) を正本として扱う
>
> **この文書は設計記録であり、enforcement の実装導入は後続 Issue へ分離する。**

---

## Goal

`personal-mcp-core` の import / layering / dependency 制約を、
runtime code に対して機械判定しやすい形へ落とす。

この文書では:

- layer / module の地図を固定する
- layer 間で許可する依存方向を明記する
- rule ごとの detection 候補と hard fail / advisory の境界を整理する

## Non-goal

- `ast-grep` / `import-linter` などの実装導入
- 既存 module 配置の大規模リファクタ
- `tests/`, `scripts/`, `docs/` の import ルール固定
- docs / policy 正本責務の整理（`#258` 側で扱う）

## 対象範囲

この文書が対象にするのは `src/personal_mcp/` 配下の runtime module のみ。

- 対象: `server.py`, `adapters/`, `tools/`, `storage/`, `core/`
- 対象外: `tests/`, `scripts/`, `docs/`, `.codex/`, `.claude/`

理由:

- runtime layer の import drift を先に止めるほうが、検出対象が明確
- test/support code は cross-layer 参照が必要になるため、同じ制約をそのまま当てにくい

---

## 1. Runtime layer map

| Layer | Main modules | Responsibility | Allowed internal imports |
|---|---|---|---|
| Entrypoint | `server.py` | CLI composition root。引数解決と layer 組み立てを担う | `adapters`, `tools`, `storage`, `core` |
| Adapters | `adapters/mcp_server.py`, `adapters/http_server.py` | 外部 protocol を repo 内の use case へ翻訳する | `tools`, `core`, same layer |
| Tools | `tools/event.py`, `tools/daily_summary.py`, `tools/log_form.py`, `tools/github_sync.py`, `tools/candidates.py`, `tools/poe2_client_watcher.py` | use case / application orchestration | `storage`, `core`, same layer |
| Storage boundary / backend | `storage/events_store.py`, `storage/path.py`, `storage/jsonl.py`, `storage/sqlite.py` | persistence, data-dir resolution, backend I/O | same layer |
| Core | `core/event.py`, `core/guide.py` | data contract, pure helper, packaged guide access | same layer only |
| Packaged data | `AI_GUIDE.md` | packaged resource | import 対象外 |

補足:

- `server.py` を唯一の composition root とみなし、他の runtime module から `server.py` を参照しない
- `storage/events_store.py` は application から見た storage boundary とし、backend 実装の詳細は `storage/jsonl.py` / `storage/sqlite.py` に閉じる
- `#258` が扱う docs/policy の責務分離は、この runtime layer map とは別軸で管理する

## 2. 許可する依存方向

許可する主方向は次のとおり。

```text
server.py
  -> adapters
  -> tools
  -> storage
  -> core

adapters
  -> tools
  -> core

tools
  -> storage
  -> core

storage
  -> storage (same layer only)

core
  -> core (same layer only)
```

禁止したい方向:

- `core` -> `storage` / `tools` / `adapters` / `server`
- `storage` -> `tools` / `adapters` / `server`
- `tools` -> `adapters` / `server`
- `adapters` -> `storage` backend / `server`
- `*` -> `server.py`（`server.py` 自身を除く）

同一 layer import は許容するが、循環依存を前提にしない。

---

## 3. Rule candidates

| ID | Rule | Intended status | Detection candidates | Notes |
|---|---|---|---|---|
| R1 | `core/*` は leaf とし、`storage` / `tools` / `adapters` / `server` を import しない | hard fail | `ast-grep`, `import-linter` | repo の下層 contract を安定させる最優先ルール |
| R2 | `storage/*` は `tools` / `adapters` / `server` を import しない | hard fail | `ast-grep`, `import-linter` | persistence 層から application / protocol 側へ逆流させない |
| R3 | `tools/*` は `adapters/*` と `server.py` を import しない | hard fail | `ast-grep`, `import-linter` | use case から protocol 実装へ逆依存させない |
| R4 | `adapters/*` は `storage/jsonl.py` / `storage/sqlite.py` / `server.py` を直接 import しない | hard fail | `ast-grep`, `import-linter` | adapter は `tools` / `core` 越しに扱う |
| R5 | `server.py` は composition root とし、他 module から import しない | hard fail | `ast-grep`, `import-linter` | CLI wiring の逆流を止める |
| R6 | `storage/events_store.py` を経由できる用途では、`tools/*` / `adapters/*` から backend (`jsonl.py` / `sqlite.py`) を直接参照しない | advisory | `ast-grep`, `rg`, review checklist | migration / read-only 例外を整理しながら段階適用する |
| R7 | 外部 interface 専用 dependency（例: MCP server library, HTTP framework）は `adapters/*` に閉じ、`core` / `tools` へ持ち込まない | advisory | `ast-grep`, `rg`, review checklist | 現在は依存追加前提ではないため、設計ガードとして先に固定する |

## 4. Hard fail / advisory の境界

### Hard fail に寄せるもの

- layer の依存方向そのものを壊す import
- `server.py` を composition root 以外から参照する import
- adapter が backend 実装へ直結する import

これらは「repo の構造 drift そのもの」を意味し、導入時点から failure の意味が明確。

### Advisory に残すもの

- `events_store.py` を経由するか、backend を直接読むかの境界
- 外部 dependency をどこまで adapter-local に閉じるか

これらは migration 中の例外や実装都合が残りやすいため、
まずは review 補助と文書ルールとして固定し、違反実態を見て hard fail 化を再評価する。

---

## 5. Detection surface の比較

| Candidate | 向いている rule | Strength | Weakness | This doc での位置づけ |
|---|---|---|---|---|
| `ast-grep` | R1-R7 | module path 単位の禁止 import や限定例外を表現しやすい | ルール保守コストは多少かかる | 初手の優先候補 |
| `import-linter` | R1-R5 | layer contract を package 単位で宣言しやすい | file 単位例外や backend 例外の表現はやや重い | 代替候補 |
| `rg` + review checklist | R6-R7 | 導入コストが最小 | deterministic hard fail にならない | advisory bootstrap 用 |

Issue #260 で整理した baseline に沿うなら、structural constraints の初手は
`ast-grep` を優先候補とし、`import-linter` は package contract が増えた時点で再比較するのが妥当。

---

## 6. 違反例 / 非違反例

### 6.1 R1 core leaf

違反例:

```python
from personal_mcp.storage.events_store import append_event
```

`core/*` が storage へ依存しており、leaf ではない。

非違反例:

```python
from personal_mcp.core.event import build_v1_record
```

`tools/*` が `core/*` の contract を参照する方向なので許容。

### 6.2 R3 tools must not depend on adapters

違反例:

```python
from personal_mcp.adapters.http_server import serve
```

`tools/*` から protocol 実装を呼んでおり、layer 逆流になる。

非違反例:

```python
from personal_mcp.storage.events_store import append_event
from personal_mcp.core.event import build_v1_record
```

`tools/*` から `storage/*` と `core/*` を使う方向なので許容。

### 6.3 R4 adapters must not import storage backends directly

違反例:

```python
from personal_mcp.storage.sqlite import read_sqlite
```

adapter が backend へ直結し、use case 境界を飛び越える。

非違反例:

```python
from personal_mcp.tools.candidates import list_candidates
from personal_mcp.core.event import ALLOWED_DOMAINS
```

adapter が tool と contract を使って request/response を組み立てる方向なので許容。

### 6.4 R5 server as composition root

違反例:

```python
from personal_mcp.server import main
```

`server.py` への逆依存が発生し、wiring と use case が混ざる。

非違反例:

```python
from personal_mcp.tools.event import event_add
```

`server.py` 側が tool を組み立てる方向なので許容。

---

## 7. Rollout proposal

1. 後続 Issue で R1-R5 を hard fail 候補として実装する
2. R6-R7 は `rg` / review checklist で advisory 運用し、例外実態を観測する
3. direct backend import の例外が整理できたら、R6 の hard fail 化を再評価する

## 関連ドキュメント

- [`docs/CODEX_RUNBOOK.md`](./CODEX_RUNBOOK.md) — verification flow と non-destructive check の実行順
- `pyproject.toml` — current `ruff` configuration
- `Makefile` — baseline check command surface
- [`docs/architecture.md`](./architecture.md) — 技術アーキテクチャの全体像
- [`docs/domain-extension-policy.md`](./domain-extension-policy.md) — 別系統の policy gate の例
- [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md) — docs / policy 側の責務境界

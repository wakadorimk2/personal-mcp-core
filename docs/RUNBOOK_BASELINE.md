# Runtime-Specific Runbook Baseline

この文書は、personal-mcp-core における **runtime 別 runbook の基準構造（baseline）** を定義します。
Claude Code・Codex CLI・Copilot CLI を含む、将来の runtime 追加時にも踏襲できる構造を示します。

共通 policy の正本は [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md) です。
本文書はその補完であり、役割境界や許可範囲の意味変更を含みません。

---

## この文書の目的と非目的

### 目的

- runtime 別 runbook に必要な基本構造を定義する
- 共通 policy（`docs/AI_ROLE_POLICY.md`）と runtime 別 runbook の責務境界を明確にする
- 新しい runtime を追加するときに踏襲できる構造基準を提供する
- 既存 runbook（`docs/CODEX_RUNBOOK.md`）をこの構造の exemplar として位置づける

### 非目的

- 役割境界（no-side-effect / side-effect）の意味変更
- 実装変更・Python スクリプトの変更
- 各 runtime の詳細 runbook 本文をフルで書き起こすこと
- 通知契約・通知イベント schema の定義変更

---

## 共通 policy と runtime 別 runbook の境界

### 共通 policy に残すもの（`docs/AI_ROLE_POLICY.md`）

| 項目 | 例 |
|---|---|
| 副作用の定義 | ファイル書き込み、Git 操作、ネットワークアクセスなど |
| 役割定義（no-side-effect / side-effect） | 許可・禁止・ルール |
| side-effect 担当の最小修正制限 | 2 サイクル、1〜2 ファイル上限など |
| GitHub 操作の許可範囲 | PR 作成・ラベル付与・禁止操作など |
| 境界変更反映順序 | 正本 → 導線 → skills/runbook |
| 標準フロー（抽象） | no-side-effect → Maintainer → side-effect → PR |
| コピペ用テンプレ（抽象） | role 別の制約・出力形式 |

### runtime 別 runbook に置くもの

| 項目 | 例 |
|---|---|
| runtime 固有のコマンド | `ruff check .`、`gh pr create`、`codex run`、`copilot` など |
| 実行環境の前提 | 認証方法、venv 前提、WSL/Linux 差異 |
| Safety Check 手順 | `git remote -v`、worktree 確認、guard スクリプトなど |
| 各ステップのコマンド例 | Review・Lint・Test・Fix・Commit・PR の具体コマンド |
| Failure Branch | 失敗パターンと対処の具体例 |
| PR Body Template | runtime の実行環境情報を含むテンプレ |
| 停止条件 | runtime 固有の停止トリガー |
| 通知運用への導線 | notify 設定や troubleshooting の参照先 |

### runbook に置かないもの

| 項目 | 理由 |
|---|---|
| 通知契約・通知イベント schema | runtime 個別事情ではなく、専用 spec に分離して管理する |
| 実装変更方針そのもの | policy / Issue / 実装差分で扱う |
| 役割境界の正本 | `docs/AI_ROLE_POLICY.md` を優先する |

通知については、runtime 別 runbook に **運用上の導線や参照先** を置いてよい一方で、
通知 payload / event / contract の正規定義は専用文書（例: [`docs/ai-notification-contract-v1.md`](./ai-notification-contract-v1.md)）
に分離して管理する。

---

## 各 runtime runbook の章立てテンプレ

runtime 別 runbook は以下の章立てを基本構造とする。

```text
# <Runtime名> RUNBOOK

<runtime の一言説明。役割境界の正本は docs/AI_ROLE_POLICY.md を参照>

## <Runtime名> がやること
## <Runtime名> がやってはいけないこと
## 停止条件

## Standard Flow

### 1. Safety Check
### 2. Review
### 3. Lint / Format
### 4. Test
### 5. Minimal Fix
### 6. Re-run
### 7. Commit
### 8. Draft PR

## Failure Branches
## PR Body Template
## 完了時に残すもの
```

no-side-effect 担当 runtime の runbook では、コマンド実行・Git 操作が禁止されるため、
`Standard Flow` は diff 提示・コマンド候補提示の形式に読み替える。
この場合も、役割境界の定義自体は `docs/AI_ROLE_POLICY.md` を正本とする。

---

## runtime ごとに差分を持たせるべき項目

| 項目 | Claude Code | Codex CLI | Copilot CLI |
|---|---|---|---|
| 役割 | no-side-effect 担当 | side-effect 担当 | TBD |
| 認証・環境 | Claude UI / API key | API key / env / `gh auth` | GitHub auth / runtime 実装に応じて確定 |
| コマンド実行 | 禁止 | 許可（検証範囲内） | TBD |
| Git 操作 | 禁止 | 許可（最小範囲） | TBD |
| PR 作成 | 禁止 | `gh pr create` | TBD |
| Safety Check | 不要（副作用なし） | `git status` + guard スクリプト | TBD |
| 出力形式 | unified diff + コマンド候補 | PR Body Template | TBD |
| 停止条件 | Issue 外変更・不確実性 | 3 回収束しない・最小修正超過 | TBD |

> Copilot CLI の詳細運用は、実際に導入する段階で確定する。現時点では TBD とし、この構造に沿って追加できることを示す。

---

## 新 runtime 追加時のチェックリスト

新しい runtime を追加するときは以下を確認する。

- [ ] `docs/AI_ROLE_POLICY.md` の役割定義に照らして、対応する役割を確認する
- [ ] runtime 固有の認証・環境前提を確認する
- [ ] 本文書の章立てテンプレに沿って `docs/<RUNTIME>_RUNBOOK.md` を作成する
- [ ] 「runtime ごとに差分を持たせるべき項目」の TBD 欄を確定値に更新する
- [ ] `docs/AI_ROLE_POLICY.md` からの導線と、既存 runbook からの相互参照を確認する
- [ ] 通知の扱いが必要な場合は、runbook には運用導線のみを置き、契約定義は専用 spec に分離する

---

## 既存 runbook との関係

### `docs/CODEX_RUNBOOK.md`

Codex CLI を対象とした runtime-specific runbook の既存 exemplar。
本文書の章立てテンプレに対応する構造を持ち、Codex CLI 固有のコマンド、停止条件、PR 手順を記載している。
全文の再設計は行わず、この baseline の exemplar として位置づけて継続利用する。

### Claude Code runbook

Claude Code（no-side-effect 担当）固有の制約は `docs/AI_ROLE_POLICY.md` のコピペ用テンプレですでに参照できる。
独立した runbook が必要になった場合は、本文書の章立てテンプレに沿って追加する。

### Copilot CLI runbook

現時点では詳細運用が未確定のため、本書では構造のみを定義する。
導入時に別 Issue で具体 runbook を確定する。

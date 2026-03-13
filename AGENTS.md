# AGENTS.md

このファイルは、このリポジトリで作業する AI runtime 共通の entrypoint です。
詳細ルールの正本を置き換えるのではなく、最初に何を読み、どの文書を優先するかを定義します。

## Purpose

- repo-wide の first-read entrypoint を 1 つに固定する
- concern ごとの source of truth を明示する
- runtime をまたいだ conflict / stop / escalation の入口を揃える

## Non-goal

- `AI_GUIDE.md` の行動原則本文を再定義しない
- `docs/AI_ROLE_POLICY.md` の許可 / 禁止 / GitHub 操作詳細を再定義しない
- `docs/AI_WORKFLOW.md` の worktree / branch / VSCode 運用詳細を再定義しない
- `CLAUDE.md` や `docs/CODEX_RUNBOOK.md` の runtime-specific 手順やコマンドを再定義しない
- 日本語化テンプレ更新、CI enforcement、runtime runbook の全面改修を含めない

## Read Order

1. `AGENTS.md`
2. `AI_GUIDE.md`
3. `docs/AI_ROLE_POLICY.md`
4. 必要に応じて `docs/AI_WORKFLOW.md`
5. 必要に応じて `docs/PLAYBOOK.md`
6. 自分が使う runtime の文書
   - Claude Code: `CLAUDE.md`
   - Codex CLI: `docs/CODEX_RUNBOOK.md`
   - 将来の runtime: 対応する runbook
7. Issue / task に直接関係するファイル

## Source of Truth Map

| Concern | Source of truth | This file's role |
|---|---|---|
| AI の行動原則・姿勢 | `AI_GUIDE.md` | 導線のみ |
| side-effect 境界・許可 / 禁止・停止条件 | `docs/AI_ROLE_POLICY.md` | 導線のみ |
| worktree / branch / VSCode 運用 | `docs/AI_WORKFLOW.md` | 導線のみ |
| AI worker の共通作業フロー | `docs/PLAYBOOK.md` | 導線のみ |
| runtime-specific 実行手順 | `CLAUDE.md`、`docs/CODEX_RUNBOOK.md`、将来の runbook | 導線のみ |

## Precedence And Conflict Handling

- `AGENTS.md` は routing 文書であり、詳細判断の正本ではない
- 同じ concern については、上の表で指定した source of truth を優先する
- runtime-specific 文書は、対応する正本と矛盾しない範囲でのみ有効とする
- 矛盾が side-effect 可否、禁止事項、停止条件に影響する場合は副作用を伴う作業を止め、人間 Maintainer にエスカレーションする
- 矛盾が文言差や導線差に限られる場合は正本を基準に読み、同期漏れを follow-up に記録する

## Why This File Exists

- 複数 runtime をまたぐと、「最初に何を読むか」が runtime ごとにずれやすい
- 既存文書は concern ごとの正本として維持し、`AGENTS.md` は入口と優先順位だけを固定する
- これにより、巨大な新正本を増やさずに導線だけを統一できる

## Migration Boundary For #372

この Issue で `AGENTS.md` に寄せるのは、次のメタ情報だけです。

- entrypoint であること
- read order
- source of truth map
- precedence / stop / escalation の入口
- 既存文書へ何を残すかの境界

この Issue で既存正本に残すもの:

- AI 行動原則の本文
- role boundary の本文
- workflow / worktree / branch の本文
- runtime-specific command / review / PR 手順

この Issue の非スコープ:

- 既存 AI 文書の全面リライト
- 日本語化テンプレの全面更新
- runtime runbook の詳細設計確定
- CI や自動 enforcement の追加

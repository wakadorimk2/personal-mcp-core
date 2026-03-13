# Docs Index

このディレクトリは、canonical source を減らしつつ参照導線を揃えるための index。
まず「何を知りたいか」で入口を選ぶ。

## 1. AI development system

- `AGENTS.md`: repo-wide entrypoint と read order
- `AI_GUIDE.md`: AI behavior principles
- `docs/architecture/ai-development-system.md`: AI development system の parent doc
- `docs/AI_ROLE_POLICY.md`: side-effect boundary の detail
- `docs/AI_WORKFLOW.md`: worktree / branch / VSCode 運用
- `docs/PLAYBOOK.md`: issue intake から handoff までの flow
- `docs/CODEX_RUNBOOK.md`: Codex の execution / review / GitHub ops

## 2. Architecture

- `docs/architecture.md`: システム全体の構造
- `docs/design-principles.md`: north star
- `docs/adapters.md`: adapter 層の補助説明
- `docs/import-layering-dependency-constraints.md`: layering 制約

## 3. Specs and contracts

- `docs/event-contract-v1.md`
- `docs/kind-taxonomy-v1.md`
- `docs/domain-extension-policy.md`
- `docs/worker-claim-protocol.md`
- `docs/worker-domain.md`
- `docs/worker-registry-coordination.md`

## 4. Runbooks and operations

- `docs/RUNBOOK_BASELINE.md`: runtime-specific runbook baseline
- `docs/data-directory.md`: data-dir / backup / restore boundary
- `docs/infra/backup-mvp-options.md`: MVP backup comparison
- `docs/infra/notify-wrapper.md`: notify wrapper の運用面

## 5. Specialized skills

以下は独立 canonical doc を維持する specialized skill。

- `docs/skills/clarify-request.md`
- `docs/skills/codex-claude-bridge.md`
- `docs/skills/implement-only.md`
- `docs/skills/issue-draft.md`
- `docs/skills/issue-split.md`
- `docs/skills/post-candidate.md`
- `docs/skills/research-propose-structured.md`

日常の execution skill は `docs/CODEX_RUNBOOK.md` に吸収した。

## 6. Historical notes policy

Issue-specific research snapshots, temporary inventories, and one-off audit notes are
not indexed here once their lasting rules have been absorbed into canonical docs.

長期に参照したい invariant は canonical doc に寄せ、短命な調査メモは Issue か一時 artifact
として扱う。

# AI Development System

> Related issue: #417
> Parent epic: #415
> Status: canonical parent for AI priming / development system boundaries

## Purpose / Scope / Non-goal

This document is the canonical parent for the repo's AI development system.
It explains how entrypoint docs, behavior principles, role boundaries,
workflow, dispatch, protocol children, and runtime runbooks fit together.
For a broader docs map, see [`docs/README.md`](../README.md).

This document does:

- define the primary read order after `AGENTS.md` and `AI_GUIDE.md`
- explain the source-of-truth topology for AI development docs
- describe the high-level role, workflow, dispatch, and escalation model
- define which concerns stay in protocol child docs and runtime runbooks

This document does not:

- replace `AGENTS.md` as the repo-wide entrypoint
- replace `AI_GUIDE.md` as the behavior-principles source of truth
- redefine runtime-specific command surfaces such as `docs/CODEX_RUNBOOK.md`
- absorb worker protocol specs such as claim event schema or registry schema
- redesign the development system beyond the boundaries already approved

## Read Order And Entry Points

When starting a task, read docs in this order:

1. `AGENTS.md`
2. `AI_GUIDE.md`
3. `docs/architecture/ai-development-system.md`
4. runtime-specific or task-specific child docs as needed
   - role / side-effect details: `docs/AI_ROLE_POLICY.md`
   - worktree / branch / VSCode operations: `docs/AI_WORKFLOW.md`
   - issue-to-handoff lifecycle: `docs/PLAYBOOK.md`
   - runtime dispatch policy: `docs/WORKER_POLICY.md`
   - worker protocol children: `docs/worker-claim-protocol.md`, `docs/worker-registry-coordination.md`, `docs/worker-domain.md`
   - runtime runbooks: `CLAUDE.md`, `docs/CODEX_RUNBOOK.md`
5. files directly related to the issue or task

Interpretation rules:

- `AGENTS.md` stays the repo-wide routing entrypoint
- `AI_GUIDE.md` stays the owner-facing behavioral source of truth
- this document is the parent doc for the development system and AI priming boundaries
- child docs should be read as adapters or focused detail docs, not parallel top-level entrypoints

## Source Of Truth Topology

| concern | canonical source | child / adapter docs |
|---|---|---|
| repo-wide entrypoint and precedence | `AGENTS.md` | `CLAUDE.md`, runtime runbooks |
| AI behavior principles | `AI_GUIDE.md` | root and packaged copies, runtime notes |
| AI development system overview | `docs/architecture/ai-development-system.md` | `docs/AI_ROLE_POLICY.md`, `docs/AI_WORKFLOW.md`, `docs/PLAYBOOK.md`, `docs/WORKER_POLICY.md` |
| worker protocol and state contracts | protocol child docs | `docs/worker-claim-protocol.md`, `docs/worker-registry-coordination.md`, `docs/worker-domain.md` |
| runtime-specific execution procedures | runtime runbooks | `CLAUDE.md`, `docs/CODEX_RUNBOOK.md` |

Adapter rule:

- canonical intent belongs in the parent doc
- child docs remain only when they carry focused detail, local appendix material, or runtime-specific procedure
- if parent and child disagree on the same concern, the parent doc wins unless the concern is explicitly delegated to a protocol child or runtime runbook

## Development System Overview

The repository's development system is organized around four layers:

1. human maintainer judgment
2. AI behavior principles and routing
3. AI development system boundaries and workflow
4. protocol specs and runtime runbooks

Practical model:

- the human Maintainer owns final decisions, overrides, and scope judgment
- `AGENTS.md` tells each runtime what to read first
- `AI_GUIDE.md` fixes attitude, prohibitions, and interaction posture
- this document explains how role boundary, workflow, dispatch, and escalation fit together
- protocol child docs define worker claim and registry specifics
- runtime runbooks define concrete execution procedures

## Role Boundary And Side-Effect Model

The system uses a side-effect boundary rather than a capability ranking.

High-level split:

- no-side-effect side: implementation proposals, research, diff suggestions
- side-effect side: verification, command execution, minimal fix, PR creation

Shared rules:

- side effects must stay within issue scope
- specification expansion, design change, and issue-scope growth do not happen during verification
- minimal fixes are limited to directly observed failures and should stay local and explainable
- if a conflict changes whether side effects are allowed, stop and escalate to the human Maintainer

Detailed boundary definitions, permission lists, and stop conditions remain in `docs/AI_ROLE_POLICY.md`.

## Workspace And Execution Flow

The development system separates environment operations from issue lifecycle.

Environment side:

- worktree is long-lived and role-based
- branch is short-lived and task-based
- VSCode windows stay aligned to worktree and role

Issue flow side:

1. intake
2. claim or ownership confirmation
3. plan
4. execute
5. verify
6. PR or review package
7. release or handoff

Interpretation:

- `docs/AI_WORKFLOW.md` carries detailed worktree / branch / VSCode operation notes
- `docs/PLAYBOOK.md` carries the detailed phase-by-phase issue lifecycle
- this parent doc exists to explain that these are parts of one development system, not separate top-level policies

## Runtime Dispatch And Reviewer Split

Runtime selection follows task-class and role-boundary alignment.

High-level expectations:

- research and implementation-diff work start on the no-side-effect side
- verification, review, and PR creation happen on the side-effect side
- implementer and reviewer should normally be separated by runtime
- fallback is conditional and never overrides role boundary or claim state

Detailed task-class matrix, fallback semantics, and collision avoidance stay in `docs/WORKER_POLICY.md`.

## Protocol Children And Runtime Docs

The following docs remain independent children rather than being absorbed here:

- `docs/worker-claim-protocol.md`
- `docs/worker-registry-coordination.md`
- `docs/worker-domain.md`
- `CLAUDE.md`
- `docs/CODEX_RUNBOOK.md`

Reason:

- protocol child docs carry their own canonical event / state / source-of-truth boundaries
- runtime docs carry runtime-specific constraints and command procedures
- this parent doc should explain where they fit, but should not duplicate or replace them

## Conflict / Stop / Escalation

Use this precedence for development-system interpretation:

1. `AGENTS.md` for repo-wide entrypoint and precedence
2. `AI_GUIDE.md` for behavior principles
3. `docs/architecture/ai-development-system.md` for development-system topology
4. delegated child docs for the concern explicitly assigned to them
5. runtime-specific runbooks for runtime procedure
6. historical notes, old templates, and issue comments

Stop and escalate when:

- two docs disagree on whether side effects are allowed
- a boundary conflict would change who is allowed to act
- a child doc appears to redefine a concern that belongs to the parent
- a runtime note conflicts with the parent or with delegated protocol specs

If wording differences do not change operational judgment, continue using the canonical source and record the synchronization gap for follow-up.

## Migration Boundary For #417

This issue moves canonical development-system meaning into this parent doc.

This issue does:

- create the parent doc
- convert `docs/AI_ROLE_POLICY.md`, `docs/AI_WORKFLOW.md`, `docs/PLAYBOOK.md`, and `docs/WORKER_POLICY.md` into adapters
- switch read order in `AGENTS.md`, `AI_GUIDE.md`, and `CLAUDE.md`
- keep worker protocol docs independent and linked

This issue does not:

- redesign worker protocol specs
- merge runtime runbooks or skill docs
- absorb the local Project Active appendix currently retained in `docs/AI_WORKFLOW.md`
- complete `docs/` index, stub, and backlink cleanup

Handoff boundary:

- runbook / skill consolidation goes to `#418`
- Project Active appendix reevaluation stays as follow-up ops-workflow work
- index / stub / backlink completion goes to `#419`

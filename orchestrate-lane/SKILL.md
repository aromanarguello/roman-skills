---
name: orchestrate-lane
description: Create and manage dedicated Codex lane threads with goals, acceptance criteria, PR babysitting, review gates, and wrap-up. Use when work should be split across Codex threads, or when an existing diff needs a manager thread to review, PR, babysit, and ship it.
---

# Orchestrate Lane

Use this skill to turn Codex from "one long chat" into a small operating system of accountable threads.

A lane is one Codex thread that owns one outcome. The parent thread is the manager: it creates lane contracts, checks status, steers blockers, and keeps PRs moving.

This skill is for Codex app threads. It is not the same as spawning short-lived subagents inside one conversation.

## Core Primitives

- **Manager thread**: the parent thread that knows the program state and coordinates workers.
- **Lane thread**: a dedicated Codex thread with one goal and one bounded scope.
- **Lane contract**: goal, acceptance criteria, scope, inputs, starting state, autonomy rules, and required workflow.
- **Heartbeat/check-in**: a scheduled or manual status pass where the manager inspects threads and moves blocked work.
- **Goal lock**: a concrete lane goal that lets the worker thread decide when it is complete, blocked, or ready for review.
- **Review gate**: final review, tests, CI, and review-bot comments before merge.
- **Wrap-up**: the closure packet that records PR, verification, what merged, and what remains.
- **Reflection loop**: a manager-side note of what worked, what stalled, and how to tighten the next lane contract.

## Manager Heartbeat Protocol

Use a heartbeat when the user wants a lane babysat after handoff, when CI/review bots are expected to take time, or when multiple lanes may drift without a manager.

A heartbeat can be manual or scheduled. If the app automation tools are available and the user wants recurring follow-up, create a recurring check-in for the manager thread instead of asking the user to remember.

Every heartbeat should:

1. Read each active lane thread only as much as needed to determine state.
2. Classify each lane as `not started`, `working`, `waiting on CI`, `waiting on review`, `blocked`, `ready to merge`, `merged`, or `needs user decision`.
3. Push the lane forward with one concrete instruction when it is stuck on a mechanical next step.
4. Enforce gates: tests/builds, final review, CI, review-bot comments, and merge authorization.
5. Avoid redoing lane work inside the manager thread unless the lane is abandoned or the user redirects ownership.
6. Report a compact status table to the user when something materially changes.
7. Capture one improvement for future orchestration if the lane contract was unclear, too broad, or missing a gate.

Heartbeat prompts should be explicit. Example:

```md
Check active lane threads. Read each worker thread only as needed.
For each lane, report state, blocker, next action, and whether it is safe to merge.
If a lane is blocked on mechanical review/CI work, send it one concrete instruction to continue.
Do not merge unless checks are green, review comments are addressed, and merge is authorized.
```

## Decide The Lane Type

Classify the request before creating threads:

- **Existing-work lane**: current uncommitted or committed work needs review, PR, babysitting, and ship/merge follow-through.
- **New-work lane**: a thread should build a new feature, slice, experiment, or operational setup from scratch.
- **Multi-lane program**: several parallel threads should each own one PR, track, or workstream.

Use Codex thread tools only when the user asks to create, spin up, start, fork, inspect, continue, or manage threads. If the tools are not already loaded, search for `create_thread`, `list_threads`, `read_thread`, `send_message_to_thread`, `set_thread_title`, and `set_thread_archived`.

## Gather Context

Collect only the context needed to make the lane autonomous:

1. Identify the repo or project path.
2. Read `git status --short`, current branch, and `git diff --stat` when code is involved.
3. For existing-work lanes, list changed tracked files and explicitly call out untracked files that should not be staged by default.
4. For new-work lanes, capture the product decision, expected deliverable, likely files/areas, and known blockers.
5. Capture verification already performed and verification still required.
6. Capture secrets policy: never print secrets, and distinguish local/test/prod env assumptions when relevant.

Do not over-research. The lane thread can investigate further inside its own scope.

## Create The Lane Contract

Every lane prompt should include these sections:

```md
## Goal
<One concrete outcome this thread owns.>

## Acceptance Criteria
- <Observable product/code/ops result.>
- <Required test/build/check proof.>
- <PR/review/merge state required.>
- <User-visible or operational proof if applicable.>

## Scope
- <Files, modules, systems, or setup surfaces this lane may touch.>

## Out Of Scope
- <Specific things not to touch unless approved.>

## Inputs
- <Relevant links, branches, prior decisions, env assumptions, PRs, screenshots, or constraints.>

## Starting State
- <Current branch/status/diff summary, or default branch/new worktree starting point.>

## Autonomy Rules
- Auto-fix mechanical and concrete review findings.
- Ask before product behavior, architecture, destructive data, billing, auth, or production-impacting changes.
- Do not stage unrelated files.
- Do not expose secrets.
- Keep the parent thread updated with concise status when milestones change.

## Heartbeat Plan
- <Manual check-in only, or scheduled cadence such as every 10 minutes while CI/review is active.>
- <What the manager must inspect: thread status, PR checks, review comments, deployments, logs, or external accounts.>
- <What requires user approval before proceeding.>

## Required Workflow
1. Implement or continue the lane work.
2. Run focused verification.
3. Run final review or the repo's equivalent pre-merge review.
4. Fix concrete findings and rerun verification.
5. Open a PR for the lane.
6. Babysit CI and review-bot comments.
7. Fix or respond to every actionable review item.
8. Merge only when clean and allowed.
9. Run the repo's ship/wrap-up workflow.
10. Wrap up with merged PR, verification, and next-state summary.
11. Leave a short reflection note if the lane exposed a reusable orchestration improvement.
```

Acceptance criteria should be concrete enough that another Codex thread can decide whether it is done without rereading the parent conversation.

## Create Threads

For existing uncommitted work:

- Prefer a working-tree thread so the lane sees the current diff.
- Tell the lane exactly which files to stage and which untracked files to ignore.

For new work:

- Prefer a fresh worktree from the project default branch unless the user asks to start from a specific branch or current working tree.
- Include the lane contract.
- Ask the lane to begin with implementation, not another broad strategy pass, unless research is explicitly the lane.

For multi-lane programs:

- Create one thread per lane.
- Give each lane a different goal and independent acceptance criteria.
- Avoid shared-file collisions by naming likely ownership boundaries.
- Tell each lane whether it should open its own PR or only produce a plan/artifact.

After successful thread creation, report the created thread or pending worktree id back to the user.

## Existing-Work Handoff Template

```md
You are taking over an existing-work lane.

## Goal
Review, polish, PR, babysit, and ship the current changes for <feature>.

## Acceptance Criteria
- Current tracked changes are reviewed.
- Mechanical/concrete findings are fixed.
- Verification passes: <commands>.
- PR includes only intended files: <files>.
- CI and review-bot comments are clean or explicitly resolved.
- PR is merged if authorized and the lane is wrapped up.

## Scope
- <tracked file 1>
- <tracked file 2>

## Out Of Scope
- Do not stage or commit <untracked/unrelated paths>.
- Do not change <adjacent systems> unless review finds a concrete blocker.

## Inputs
- <prior PRs, screenshots, env assumptions, user decisions>

## Starting State
- Repo: <path>
- Branch: <branch>
- Status: <git status summary>
- Diff stat: <git diff --stat summary>
- Verification already run: <commands/results>

## Autonomy Rules
<rules>

## Heartbeat Plan
<manual/scheduled check-in cadence and gates>

## Required Workflow
<steps>
```

## New-Work Lane Template

```md
You own one new-work lane.

## Goal
Build <specific feature/slice> and take it through PR readiness.

## Acceptance Criteria
- <Feature behavior works locally or in tests.>
- <Instrumentation, docs, or ops proof exists if applicable.>
- <Tests/build/checks pass.>
- Final review has no unresolved blockers.
- PR is opened, review comments are addressed, and the lane is ready to ship or shipped if authorized.

## Scope
- Likely areas: <paths/modules>.

## Out Of Scope
- <non-goals and collision boundaries>.

## Inputs
- <product decisions, UI copy, pricing, event names, tickets, links>.

## Starting State
- Start from <default branch/current branch/specified branch>.

## Autonomy Rules
<rules>

## Heartbeat Plan
<manual/scheduled check-in cadence and gates>

## Required Workflow
<steps>
```

## Babysit Rules

Once a PR exists, the lane thread should:

- Poll required CI/checks and report failures with exact check names.
- Inspect review comments from GitHub and review bots such as CodeRabbit, Bugbot, and Greptile when available.
- Fix actionable code comments in commits.
- Reply or document why non-actionable or incorrect comments are not applied.
- Rerun focused verification after fixes.
- Merge only when the PR is mergeable, required checks pass, and no actionable review items remain.

## Parent Thread Duties

The parent thread remains mission control:

- Keep a compact list of lanes, thread ids, goals, and current states.
- Keep a heartbeat cadence when lanes are waiting on CI, review bots, deployment, or external account work.
- Read lane threads when the user asks for status.
- Send messages to lane threads when priorities change.
- Avoid duplicating implementation work already owned by a lane.
- Surface blockers that require product, account-level, security, billing, or destructive-data decisions.
- Archive or close lanes only after a real wrap-up.
- After the program ends, summarize which primitives worked: thread split, goals, heartbeat, gates, review loop, and wrap-up.

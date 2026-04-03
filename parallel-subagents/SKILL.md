---
name: parallel-subagents
description: "Spawn multiple subagents in a single message to execute independent tasks concurrently, then aggregate their results into a unified summary. Supports three modes: Explore agents for codebase research, general-purpose agents for quick standalone tasks, and test runners for parallel suite execution. Use when you have 2+ independent tasks like 'parallel research', 'explore in parallel', 'investigate multiple areas', or 'run tests in parallel'. NOT for plan execution (use subagent-driven-development instead)."
---

# Parallel Subagents

Orchestrate multiple subagents for ad-hoc parallel work: research, quick tasks, or test execution.

**Core principle:** One focused agent per topic, all dispatched in a single message, results synthesized after.

## When to Use

Use **parallel-subagents** when you have 2+ independent tasks with no shared state and no written plan. Otherwise:

| Scenario | Use Instead |
|----------|-------------|
| Have a written plan | `subagent-driven-development` |
| 3+ independent test failures | `dispatching-parallel-agents` |
| Tasks depend on each other | Sequential execution |

## Mode Selection

| Mode | Subagent Type | Model | Use When |
|------|---------------|-------|----------|
| **Research** | Explore | haiku | Investigating codebase, gathering info, understanding patterns |
| **Quick tasks** | general-purpose | sonnet | Small independent tasks, no formal review needed |
| **Testing** | general-purpose | haiku | Running test suites across packages |

## The Pattern

### 1. Identify Independent Tasks

List what needs to happen. Verify independence:
- Can each complete without results from others? ✓
- No shared files being edited? ✓
- No sequential dependencies? ✓

### 2. Scope Each Task

Each agent gets:
- **Specific focus:** One topic/file/feature
- **Clear deliverable:** What to return
- **Constraints:** What NOT to explore/touch

**Bad scope:** "Investigate the codebase" (infinite)
**Good scope:** "Find how authentication middleware validates JWTs" (bounded)

### 3. Dispatch in Parallel

**Critical: Single message, multiple Task tool calls!**

All Task tool invocations must be in the same response to achieve true parallelism. Sequential messages = sequential execution.

### 4. Synthesize Results

After all agents return:
- Read each summary
- Identify patterns across findings
- Note conflicts or inconsistencies
- Create unified understanding
- Identify gaps for follow-up

## Research Mode Template

Use Explore agents (haiku, read-only) for investigation:

```
Task tool:
  subagent_type: Explore
  model: haiku
  description: "Research [topic]"
  prompt: |
    Investigate [specific topic] in this codebase.

    Focus on:
    - [Specific question 1]
    - [Specific question 2]

    Return:
    - Key findings (files, patterns, conventions)
    - Code examples with file:line references
    - Gaps or areas needing deeper investigation
```

## Quick Tasks Mode Template

Use general-purpose agents for small independent work:

```
Task tool:
  subagent_type: general-purpose
  model: sonnet
  description: "Implement [task]"
  prompt: |
    [Task description]

    This is a quick standalone task. Implement, test, commit.

    Return: What you did, files changed, any issues.
```

**Note:** For tasks requiring spec compliance review and code quality review, use `subagent-driven-development` instead.

## Testing Mode Template

Run tests across packages in parallel:

```
Task tool:
  subagent_type: general-purpose
  model: haiku
  description: "Run [package] tests"
  prompt: |
    Run tests for [package/area].

    Command: [test command]

    Return: Pass/fail count, any failures with error messages.
```

## Red Flags

| Mistake | Why It's Wrong |
|---------|----------------|
| **Sequential dispatch** | Using multiple messages instead of one defeats parallelism |
| **Vague scope** | "Look into the codebase" has no bounds — agents will explore forever |
| **Dependent tasks** | Task B needs Task A's result → must run sequentially |
| **Overlapping edits** | Multiple agents editing same files → merge conflicts |
| **Skipping synthesis** | Results come back but you move on without integrating findings |

## Example: Parallel Research

User asks: "Research how auth, database, and API work in this codebase"

**Dispatch (single message with 3 Task calls):**

```
Task 1:
  subagent_type: Explore
  model: haiku
  description: "Research auth patterns"
  prompt: |
    Investigate authentication in this codebase.
    Focus on: middleware, decorators, JWT handling, session management.
    Return: Key files, patterns used, code examples with file:line refs.

Task 2:
  subagent_type: Explore
  model: haiku
  description: "Research database layer"
  prompt: |
    Investigate the database layer in this codebase.
    Focus on: ORM used, schema location, query patterns, migrations.
    Return: Key files, patterns used, code examples with file:line refs.

Task 3:
  subagent_type: Explore
  model: haiku
  description: "Research API conventions"
  prompt: |
    Investigate API conventions in this codebase.
    Focus on: route structure, controllers/handlers, validation, error handling.
    Return: Key files, patterns used, code examples with file:line refs.
```

**After agents return:** Synthesize findings into unified architecture understanding.

## Example: Parallel Tests

User asks: "Run all test suites"

**Dispatch (single message):**

```
Task 1:
  subagent_type: general-purpose
  model: haiku
  description: "Run API tests"
  prompt: Run `pnpm api:test` and report pass/fail counts with any failures.

Task 2:
  subagent_type: general-purpose
  model: haiku
  description: "Run web tests"
  prompt: Run `pnpm --filter web test` and report pass/fail counts with any failures.

Task 3:
  subagent_type: general-purpose
  model: haiku
  description: "Run clips tests"
  prompt: Run `pnpm clips:test` and report pass/fail counts with any failures.
```

**After agents return:** Aggregate results into test summary.

---
name: codex
description: Use when user wants to delegate a task to OpenAI Codex CLI. Triggers on "ask codex", "have codex", "codex:", "send to codex", "let codex", "run codex". Delegates via subagent to keep main context clean.
---

# Codex Delegation

Delegate tasks to OpenAI's Codex CLI via a subagent. Codex runs non-interactively and results are summarized back.

## Routing

```
Is this a code review request?
       │
  ┌────┴────┐
  yes       no
  │         │
  ▼         ▼
codex       codex exec
review      --sandbox read-only
```

## Execution

Dispatch a **single Bash subagent** (Task tool) with the appropriate command. This keeps all Codex output isolated from the main context window.

### For code reviews

Use `codex review` which has specialized review behavior:

```
Task tool:
  subagent_type: Bash
  model: haiku
  description: "Codex review"
  prompt: |
    Run this command and return the full output:

    codex review {FLAGS} "{INSTRUCTIONS}" -o /tmp/codex-out.txt 2>/dev/null; cat /tmp/codex-out.txt

    Flags:
    - --uncommitted  → review staged/unstaged/untracked changes
    - --base BRANCH  → review changes against a base branch
    - --commit SHA   → review a specific commit

    Default to --uncommitted if user didn't specify.
    Return the complete review output.
```

### For everything else

Use `codex exec` in read-only sandbox:

```
Task tool:
  subagent_type: Bash
  model: haiku
  description: "Codex: {brief task}"
  prompt: |
    Run this command and return the full output:

    codex exec "{USER_PROMPT}" --sandbox read-only -C "{WORKING_DIR}" -o /tmp/codex-out.txt 2>/dev/null; cat /tmp/codex-out.txt

    Return the complete output.
```

### If user wants Codex to make changes

User must explicitly ask for write access. Use `--sandbox workspace-write` instead of `read-only`:

```
codex exec "{PROMPT}" --sandbox workspace-write -C "{WORKING_DIR}" -o /tmp/codex-out.txt 2>/dev/null; cat /tmp/codex-out.txt
```

## After Subagent Returns

1. Read the subagent's output
2. Present a **concise summary** to the user
3. Include key findings, recommendations, or answers
4. Mention if Codex flagged any critical issues (P0/P1)

## Quick Reference

| User Says | Route To | Flags |
|-----------|----------|-------|
| "ask codex to review" | `codex review` | `--uncommitted` |
| "codex review against main" | `codex review` | `--base main` |
| "codex review commit abc123" | `codex review` | `--commit abc123` |
| "ask codex to analyze/explain/plan" | `codex exec` | `--sandbox read-only` |
| "have codex fix/refactor/implement" | `codex exec` | `--sandbox workspace-write` |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running codex in main context | Always use a Bash subagent via Task tool |
| Forgetting `2>/dev/null` | Codex thinking tokens flood context without this |
| Forgetting `-o` flag | Without it, output mixes with metadata noise |
| Using interactive mode | Always use `codex exec` or `codex review`, never bare `codex` |
| Hardcoding model | Let user's codex config choose the model |

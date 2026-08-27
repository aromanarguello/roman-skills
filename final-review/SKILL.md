---
name: final-review
description: Pre-merge review that runs PR quality, tech debt, security, regression, and performance analysis in parallel via general-purpose agents, aggregates findings into a unified prioritized report, then auto-fixes mechanical issues. Use when the user says "final review", "pre-merge review", "run all reviews", or wants a comprehensive check before merging. Defaults to all reviewers; accepts args to run a subset (e.g., `/final-review security techdebt`).
---

# Final Review

Run multiple concern-specific reviews in parallel against the current diff, then aggregate findings into one prioritized report and auto-fix the mechanical ones.

## Arguments

`$ARGUMENTS`

- `pr-review` — code quality, tests, types, error handling, naming
- `techdebt` — duplicated code, dead code, over-abstractions
- `security` — auth bypass, injection, secrets, unsafe deserialization
- `regression` — dependency trace, blast radius, untested impact
- `performance` — N+1 queries, expensive hot paths, bundle size, memory leaks
- `all` or no args — run all reviewers (default)

Multiple args are space-separated: `/final-review security techdebt`

## Workflow

### 1. Determine scope

Run `git diff --name-only` (staged + unstaged) to identify changed files. If the working tree is clean, fall back to `git diff --name-only HEAD~1 HEAD` to review the last commit. Pass this list to each reviewer so they focus on the right files.

### 2. Parse arguments

If `$ARGUMENTS` is empty or contains `all`, run all reviewers. Otherwise, run only the reviewers listed.

### 3. Launch reviewers in parallel

Spawn each selected reviewer as a **background general-purpose Agent** so they run concurrently. All Agent calls go in a single message to achieve true parallelism.

**PR Review:**

```
Agent({
  description: "PR quality review",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: `Review the diff in the changed files for code quality issues. Focus on:
- Test coverage gaps for new code
- Comments that lie about behavior or duplicate code
- Inadequate error handling and silent failures
- Type safety issues (any, unknown, missing types)
- Code that violates conventions in nearby files
- Functions that are too long, too nested, or too coupled

For changed functions with complex branching, perform a semantic branching audit. Look for nested conditions, boolean mode flags, repeated checks, mixed validation/policy/execution, accumulated special cases, and behavior paths without matching tests. For every branching-complexity finding:
1. Name the independent decisions mixed together.
2. Explain which behavior paths create maintenance or regression risk.
3. Identify the missing tests for those paths.
4. Recommend a simplification that removes real decisions, duplication, or concepts.

Do not flag branching merely because it exists; exhaustive state handling, validation guards, and explicit business rules may be appropriate. Do not recommend extracting one-use helpers that only move decision paths elsewhere. Do not install or require a complexity analyzer. If the repository already reports a complexity metric, use it only as supporting evidence—not as a universal threshold or merge gate.

Changed files: <files>

Return findings as: severity (CRITICAL/HIGH/MEDIUM/LOW), file:line, description, recommendation.`
})
```

**Tech Debt:**

```
Agent({
  description: "Tech debt scan",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: `Scan the diff for tech debt. Run the skill "techdebt" via the Skill tool if available; otherwise look for:
- Duplicated logic across the changed files
- Dead code (exports never imported, unreachable branches)
- Over-abstractions (single-use helpers, pass-through wrappers)
- Magic numbers or copy-pasted string literals

Changed files: <files>

Return findings as: severity, file:line, description, recommendation.`
})
```

**Security:**

```
Agent({
  description: "Security review",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: `Review the diff for security vulnerabilities. Cover:
- Injection (SQL, command, template, path traversal)
- Auth bypass and authorization gaps
- Secrets/keys committed to code
- Unsafe deserialization (pickle, yaml.load, eval)
- XSS in templated HTML or dangerouslySetInnerHTML
- Open redirects and SSRF where host/protocol is user-controlled

Skip: DoS, rate limiting, theoretical issues, regex DoS, log spoofing, findings in markdown docs.

Changed files: <files>

Return only HIGH-confidence findings (>80% sure exploitable). Format: severity, file:line, category, description, exploit scenario, recommendation.`
})
```

**Regression:**

```
Agent({
  description: "Regression detection",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: `Trace blast radius from the changed files. Identify:
- What other files import the changed symbols
- Behavior callers depend on that this diff might break
- Tests that exist for changed code, and tests that DON'T exist but should
- Untested code paths reachable from the changes

Changed files: <files>

Return: severity, file:line, who depends on this, what could break, what's tested vs. not.`
})
```

**Performance:**

```
Agent({
  description: "Performance audit",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: `Audit the diff for performance issues. Cover:
- N+1 queries (loops that fetch from DB per item)
- Missing indexes for new query patterns
- Expensive operations in hot paths (sync I/O, heavy computation)
- Bundle size impact (large new imports, missing code splitting)
- Memory leaks (event listeners, intervals, refs not cleaned up)

Changed files: <files>

Return findings as: severity, file:line, description, expected impact, recommendation.`
})
```

### 4. Aggregate results

Once all agents complete, combine findings into a single report. Deduplication rules:

- Same file:line + same concern → keep highest severity, note both sources
- Same file:line + different concerns → keep both as separate findings
- Different files, same root cause → keep separate, optionally cross-reference

### 5. Present unified report

Use this format:

```markdown
# Final Review

## CRITICAL (must fix before merge)
- **[source]** `file:line` — description
  Recommendation: ...

## HIGH (should fix)
- **[source]** `file:line` — description
  Recommendation: ...

## MEDIUM (consider fixing)
- **[source]** `file:line` — description
  Recommendation: ...

## LOW / INFO (note for later)
- **[source]** `file:line` — description

## Strengths
- What's well-done in this diff

## Summary
- X critical, Y high, Z medium, W low findings
- Reviewers run: [list]
- Recommendation: merge / fix criticals first / needs rework
```

Where `[source]` is one of: `pr-review`, `techdebt`, `security`, `regression`, `performance` (or multiple if deduplicated: `pr-review + security`).

### 6. Auto-fix mechanical findings

After presenting the report, fix mechanical findings without waiting for user confirmation.

**Always auto-fix (any severity):**

- Dead code, unused imports, unused variables
- Code duplication (extract or deduplicate when straightforward)
- Trivial cleanup (formatting, obvious typos in code)

**Auto-fix when recommendation is concrete (CRITICAL/HIGH/MEDIUM):**

- Missing null checks or error handling
- Missing index additions
- N+1 query fixes (eager loading, batching)
- Type narrowing / type safety improvements
- Missing cleanup in `useEffect` hooks
- Any finding with a specific, mechanical change

Do not auto-fix code solely to reduce a complexity score or make a function shorter. A branching-complexity fix must remove real decisions, duplication, or state concepts while preserving behavior; moving the same decisions into one-use helpers is not a fix.

**Pause to ask the user:**

- Architectural decisions (extract a service, restructure modules)
- Ambiguous intent (might be intentionally nullable, deliberately scoped)
- Behavior changes whose impact isn't obvious from the diff
- Two valid approaches with no clear winner

After fixes, summarize what was changed and what still needs user input.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Dispatching reviewers sequentially | All Agent calls in a single message — sequential dispatch defeats parallelism |
| Forgetting `run_in_background: true` | Without it, the orchestrator blocks on each agent in turn |
| Skipping aggregation | Returning raw per-reviewer reports buries duplicates and obscures priority |
| Asking before auto-fixing mechanical findings | The whole point is to leave fewer mechanical TODOs — only pause on genuine ambiguity |
| Treating every finding as equal | Severity drives the merge recommendation; flatten the list and the user can't act |

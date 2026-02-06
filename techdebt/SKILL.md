---
name: techdebt
description: Use at end of coding sessions to find and eliminate duplicated code, dead code, and unnecessary abstractions. Also use when codebase feels cluttered or when you suspect copy-paste patterns have accumulated.
---

# Tech Debt Hunter

Find and kill duplicated code, dead code, and unnecessary complexity.

## When to Use

- End of coding session (run `/techdebt` before wrapping up)
- After implementing multiple related features
- When codebase feels cluttered or repetitive
- Before major refactoring to establish baseline

## Process

```dot
digraph techdebt {
    rankdir=TB;

    "Start /techdebt" [shape=box];
    "Scope: changed files or full scan?" [shape=diamond];
    "Get recently modified files" [shape=box];
    "Scan entire codebase" [shape=box];
    "Find duplications" [shape=box];
    "Find dead code" [shape=box];
    "Find over-abstractions" [shape=box];
    "Present findings with severity" [shape=box];
    "User picks what to fix" [shape=diamond];
    "Apply fixes" [shape=box];
    "Verify no regressions" [shape=box];
    "Done" [shape=box];

    "Start /techdebt" -> "Scope: changed files or full scan?";
    "Scope: changed files or full scan?" -> "Get recently modified files" [label="session"];
    "Scope: changed files or full scan?" -> "Scan entire codebase" [label="full"];
    "Get recently modified files" -> "Find duplications";
    "Scan entire codebase" -> "Find duplications";
    "Find duplications" -> "Find dead code";
    "Find dead code" -> "Find over-abstractions";
    "Find over-abstractions" -> "Present findings with severity";
    "Present findings with severity" -> "User picks what to fix";
    "User picks what to fix" -> "Apply fixes" [label="yes"];
    "User picks what to fix" -> "Done" [label="skip"];
    "Apply fixes" -> "Verify no regressions";
    "Verify no regressions" -> "Done";
}
```

## What to Hunt

### 1. Duplicated Code
- Copy-pasted functions with minor variations
- Similar logic in multiple files
- Repeated patterns that should be abstracted

**Detection approach:**
- Compare function bodies for similarity
- Look for identical string literals, magic numbers
- Find parallel if/else or switch structures

### 2. Dead Code
- Unused imports
- Unreachable code paths
- Commented-out code blocks
- Functions never called
- Exports never imported

### 3. Over-Abstractions
- Single-use helpers that add indirection
- Wrapper functions that just pass through
- Abstractions for "future flexibility" never used
- Deep inheritance for simple operations

## Output Format

Present findings as a prioritized list:

```
## Tech Debt Found

### High Priority (fix now)
1. **Duplicated validation logic** in `auth.ts:45` and `api.ts:120`
   - 15 lines identical, only differ in error message
   - Suggestion: Extract to `validateRequest()` helper

### Medium Priority (consider fixing)
2. **Dead export** `formatDate` in `utils.ts:30`
   - Exported but never imported anywhere
   - Suggestion: Remove or make internal

### Low Priority (note for later)
3. **Similar patterns** in handlers `userHandler.ts`, `orderHandler.ts`
   - Could share base class but works fine as-is
```

## Execution

When user runs `/techdebt`:

1. **Determine scope**
   - Default: Files modified in current git session (`git diff --name-only HEAD~10`)
   - Full scan if user specifies or working directory is small

2. **Run analysis**
   - Use parallel agents for each category
   - Cross-reference findings to avoid duplicates

3. **Present findings**
   - Group by severity
   - Include file:line references
   - Show concrete suggestions

4. **Interactive cleanup**
   - Ask which items to address
   - Apply fixes one category at a time
   - Run tests after each batch

## Quick Commands

| Command | Description |
|---------|-------------|
| `/techdebt` | Scan session changes |
| `/techdebt full` | Scan entire codebase |
| `/techdebt --duplicates` | Only find duplications |
| `/techdebt --dead` | Only find dead code |

## Integration with Session End

Pair with `wrap-up` skill:
1. Run `/techdebt` first
2. Fix high-priority items
3. Then run wrap-up for notes

## What NOT to Report

- Style inconsistencies (leave for linters)
- Performance optimizations (different concern)
- Test code duplication (often intentional)
- Generated files

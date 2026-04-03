---
name: techdebt
description: "Scan for duplicated code, dead exports, unused imports, and over-abstractions, then present prioritized findings with file:line references and apply interactive fixes with regression verification. Use at end of coding sessions, after implementing multiple related features, when the codebase feels cluttered, or when copy-paste patterns have accumulated."
---

# Tech Debt Hunter

Find and eliminate duplicated code, dead code, and unnecessary complexity.

## When to Use

- End of coding session (run `/techdebt` before wrapping up)
- After implementing multiple related features
- When codebase feels cluttered or repetitive
- Before major refactoring to establish baseline

## Workflow

1. **Scope** → 2. **Detect** → 3. **Present** → 4. **Fix** → 5. **Verify**

### 1. Determine Scope

```bash
# Default: files changed in current session
git diff --name-only HEAD~10

# Full scan: all source files
git ls-files '*.ts' '*.js' '*.py' '*.go' '*.rs'
```

Use `/techdebt full` for entire codebase, or `/techdebt --duplicates` / `/techdebt --dead` to target one category.

### 2. Detect Issues

Run detection in parallel (one agent per category):

**Duplicated code:**
```bash
# Find functions with similar bodies across files
grep -rn "function\|def \|fn " --include="*.ts" --include="*.py" | sort
# Compare repeated string literals and magic numbers
grep -rn "TODO\|FIXME\|HACK" --include="*.ts" --include="*.py"
```

**Dead code:**
```bash
# Find exports never imported elsewhere
grep -rn "export " --include="*.ts" | while read line; do
  symbol=$(echo "$line" | grep -oP '(?<=export (function|const|class) )\w+')
  [ -n "$symbol" ] && count=$(grep -rn "$symbol" --include="*.ts" | wc -l)
  [ "$count" -le 1 ] && echo "Possibly dead: $line"
done

# Find unused imports (TypeScript/JavaScript)
grep -rn "^import " --include="*.ts" --include="*.js"
```

**Over-abstractions:** Look for single-use helpers, pass-through wrappers, and "future flexibility" abstractions by checking call-site counts for exported functions.

### 3. Present Findings

Group by severity with `file:line` references:

```
### High Priority (fix now)
1. **Duplicated validation logic** in `auth.ts:45` and `api.ts:120`
   - 15 lines identical, only differ in error message
   - Suggestion: Extract to `validateRequest()` helper

### Medium Priority (consider fixing)
2. **Dead export** `formatDate` in `utils.ts:30`
   - Exported but never imported anywhere
   - Suggestion: Remove or make internal

### Low Priority (note for later)
3. **Similar patterns** in `userHandler.ts`, `orderHandler.ts`
   - Could share base class but works fine as-is
```

### 4. Interactive Cleanup

- Ask user which items to address
- Apply fixes one category at a time
- Run project test command after each batch

### 5. Verify No Regressions

```bash
# Run the project's test suite after each fix batch
# If tests fail: revert the last batch, report which fix caused the failure,
# and ask user whether to skip that fix or attempt an alternative approach
```

If tests fail after a fix, **revert that batch** (`git checkout -- <files>`), report the failure with the specific test output, and ask the user before retrying.

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

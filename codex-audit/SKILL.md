---
name: codex-audit
description: Deep code audit via Codex with full-access sandbox and validation gate. Triggers on "codex audit", "deep review", "audit with codex", "thorough code review", "/codex-audit". Unlike /codex, this gives Codex full access to run tests and explore, then validates every finding before presenting.
allowed-tools: Bash(git:*), Bash(codex:*), Read, Grep, Glob, Agent
---

# Codex Audit

Deep code review via Codex CLI with a validation gate. Codex gets full repo access to run tests, read files, and search — then Claude cross-checks every finding against actual source and project docs before presenting results.

## Step 1: Gather the Diff

```bash
# Try uncommitted changes first
DIFF=$(git diff HEAD)

# Fall back to last commit if working tree is clean
if [ -z "$DIFF" ]; then
  DIFF=$(git diff HEAD~1 HEAD)
  SCOPE="last commit"
else
  SCOPE="uncommitted changes"
fi
```

Also run `git log --oneline -5` to understand recent commit context.

## Step 2: Summarize Changes

Review the diff and write a 2-3 sentence summary of what changed. This becomes the `<DIFF_SUMMARY>` passed to Codex.

## Step 3: Dispatch Codex

Run via a **Bash subagent** (Task tool) to keep output isolated from main context:

```
Task tool:
  description: "Codex deep audit"
  prompt: |
    Run this command and return the full output:

    git diff HEAD | codex exec --full-auto \
      -s danger-full-access \
      -C "$(pwd)" \
      "You are a code reviewer. The following diff is piped to your stdin. Review it for: bugs, security issues, performance problems, logic errors, and style concerns. Be specific about file names and line numbers. You can read files, run tests, search the web for relevant docs, or do whatever you need for a thorough review. If everything looks good, say so. Here is context about what changed: <DIFF_SUMMARY>" \
      -o /tmp/codex-audit-out.txt 2>/dev/null; cat /tmp/codex-audit-out.txt

    If git diff HEAD is empty, use: git diff HEAD~1 HEAD | codex exec ...

    Return the complete output.
```

## Step 4: Validate Every Finding

This is the critical step. Codex operates with zero project context — it WILL flag intentional design choices as bugs and invent issues from misreadings.

For EACH finding Codex returns:

1. **Read the actual source code** at the file/line referenced — confirm the issue exists as described
2. **Check project docs** (CLAUDE.md, specs in `docs/`, README, design docs) — is this an intentional choice?
3. **Ask yourself**: "Is this a real bug, or is Codex misunderstanding context?" and "Even if real, is this meaningful or trivial noise?"

Classify each finding:
- **Confirmed** — verified in source, not an intentional choice, meaningful impact
- **Likely false positive** — misread, hallucinated, or conflicts with project intent (include why)

## Step 5: Present Results

Present findings grouped by classification:

### Confirmed Issues
For each: what it is, where (file:line), why you believe it's legitimate.

### Likely False Positives
For each: what Codex flagged, why you think it's wrong (with evidence).

### If All Clear
If Codex found nothing, or all findings failed validation, say so explicitly.

Then ask: "Want me to address any of these?"

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trusting Codex output blindly | ALWAYS validate — step 4 is not optional |
| Running in main context | Use a Bash subagent via Task tool |
| Forgetting `2>/dev/null` | Codex thinking tokens flood context |
| Forgetting `-o` flag | Output mixes with metadata noise |
| Skipping project doc check | Codex lacks context — you must supply it |
| Labeling style nits as confirmed | Only confirm meaningful issues |

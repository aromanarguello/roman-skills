---
name: codex-iterative
description: Multi-round iterative review via Codex CLI with session resumption — Codex reviews a plan, design, or diff, returns a verdict (APPROVED/REVISE), and Claude fixes issues and resubmits until Codex approves. Codex remembers all prior feedback across rounds via session resume, so it verifies fixes rather than re-discovering the same issues. MUST use this skill when the user wants Codex to review a plan, design doc, architecture proposal, or diff iteratively with multiple rounds of feedback. Trigger phrases include "codex iterative review", "iterative review", "review my plan with codex", "have codex review this iteratively", "multi-round review", "review until approved", "get codex to tear it apart", "codex review and verify fixes", "not just a single pass", "keep reviewing until it's solid", or "/codex-iterative". Also trigger when the user asks for a Codex review where they want verification that fixes address prior feedback, session persistence across review rounds, or accumulated context. Do NOT trigger for quick one-shot codex reviews (/codex), deep code audits (/codex-audit), codex delegation for non-review tasks, or when the user explicitly says they want a single pass.
---

# Codex Iterative Review

Multi-round review loop where Codex CLI reviews content (plans, diffs, designs), returns a verdict, and Claude iterates until Codex approves — with **session resumption** so Codex remembers all prior feedback and can verify fixes rather than re-discovering issues.

This is different from `/codex` (single fire-and-forget) and `/codex-audit` (single deep review with validation). Here, Codex and Claude have a conversation: Codex flags problems, Claude fixes them, Codex checks the fixes and may flag new issues, and so on until the content is solid.

## When to use this vs other Codex skills

| Skill | Rounds | Codex remembers prior feedback | Best for |
|-------|--------|-------------------------------|----------|
| `/codex` | 1 | No | Quick delegation, simple questions |
| `/codex-audit` | 1 | No | Deep code audit with Claude validation |
| `/codex-iterative` | Up to 3 | Yes (session resume) | Plans, designs, complex diffs that benefit from back-and-forth |

## Step 1: Prepare the content

Determine what's being reviewed and write it to a temp file so Codex can reference it cleanly.

**Plan review** (most common): Write the current plan or design to `/tmp/codex-review-content.md`. Include enough context for Codex to understand what's being built — the plan itself, relevant constraints, and what kind of feedback you want.

**Diff review**: Capture the diff:
```bash
# Uncommitted changes
git diff HEAD > /tmp/codex-review-content.md

# Or last commit if working tree is clean
git diff HEAD~1 HEAD > /tmp/codex-review-content.md
```

**File review**: Copy the target file(s) or their relevant sections into `/tmp/codex-review-content.md`.

Also write a brief context summary (2-3 sentences) explaining what this content is, what the project does, and what kind of review you want. This compensates for Codex having zero project context.

## Step 2: Round 1 — initial review

Dispatch via a Bash subagent to keep Codex output isolated from the main context:

```
Agent tool:
  description: "Codex iterative review round 1"
  prompt: |
    Run this command and return the COMPLETE output (both the JSON events and the -o file):

    codex exec --json --sandbox read-only \
      -C "{WORKING_DIR}" \
      "You are reviewing the following content for a project. Here is the context: {CONTEXT_SUMMARY}

    Review this thoroughly for: architectural issues, logic errors, missing edge cases, security concerns, unclear requirements, and anything that could cause problems during implementation.

    For each issue found, be specific: describe what's wrong, where it is, and suggest a fix.

    End your response with exactly one of:
    VERDICT: APPROVED — if the content is solid and ready to proceed
    VERDICT: REVISE — if there are issues that should be addressed before proceeding

    The content to review is in /tmp/codex-review-content.md" \
      -o /tmp/codex-review-out.txt 2>/dev/null

    First, output the JSON events (to capture the thread_id):
    cat the JSON output that was printed to stdout during execution.

    Then output the review:
    cat /tmp/codex-review-out.txt

    Return ALL of this output.
```

### Capturing the thread_id

The `--json` flag causes Codex to emit JSONL events to stdout. The first event contains the session ID:
```json
{"type":"thread.started","thread_id":"019d34f3-788f-7073-a4a1-4a928c615b06"}
```

Extract and save this `thread_id` — it's the key to session resumption in subsequent rounds.

### Parsing the verdict

Read Codex's review output and look for the verdict line at the end:
- `VERDICT: APPROVED` → proceed to Step 4 (present results)
- `VERDICT: REVISE` → proceed to Step 3 (iterate)
- No verdict found → treat as REVISE and note that Codex didn't follow the format

## Step 3: Iterate (rounds 2-3)

For each revision round:

1. **Analyze Codex's feedback** — understand what was flagged and why
2. **Update the content** — address the issues in the plan/diff/design. Write the updated version back to `/tmp/codex-review-content.md`
3. **Resume the Codex session** — this is where session resumption shines. Codex keeps its full conversation history, so it can verify whether previous issues were actually fixed:

```
Agent tool:
  description: "Codex iterative review round {N}"
  prompt: |
    Run this command and return the COMPLETE output:

    codex exec resume {THREAD_ID} --json --sandbox read-only \
      -C "{WORKING_DIR}" \
      "I've addressed your feedback. The updated content is in /tmp/codex-review-content.md. Please:
    1. Verify that previously flagged issues have been resolved
    2. Check for any new issues introduced by the changes
    3. Flag anything you missed in the previous round

    End your response with exactly one of:
    VERDICT: APPROVED
    VERDICT: REVISE" \
      -o /tmp/codex-review-out.txt 2>/dev/null

    cat /tmp/codex-review-out.txt
```

4. **Check the verdict** — if APPROVED, go to Step 4. If REVISE and under max rounds, repeat Step 3. If max rounds (3) reached, go to Step 4 with whatever state we're in.

### Why 3 rounds max

Most substantive issues surface in round 1. Round 2 catches regressions from fixes and things Codex missed initially. Round 3 is a safety net. Beyond that, diminishing returns set in and you risk Codex nitpicking rather than finding real problems. If 3 rounds aren't enough, the content likely needs a more fundamental rethink — surface that to the user rather than looping further.

## Step 4: Present results

After the loop completes (either by APPROVED verdict or max rounds), present a structured summary:

### If APPROVED

```
Codex approved after {N} round(s).

**Round 1 findings** (all resolved):
- [issue 1] — fixed by [change]
- [issue 2] — fixed by [change]

**Final verdict:** APPROVED — content is ready to proceed.
```

### If max rounds reached without approval

```
Codex did not fully approve after {N} rounds.

**Resolved issues:**
- [issue] — fixed by [change]

**Remaining concerns:**
- [issue] — Codex's concern: [what], my assessment: [agree/disagree and why]

**Recommendation:** [whether to proceed, address remaining items, or rethink the approach]
```

### Validation (borrowed from /codex-audit)

For any finding that persists to the final round, do a quick sanity check: read the actual source/plan and confirm the issue is real and not Codex misunderstanding project context. Codex has zero context about your project's intentional design choices — it will sometimes flag things that are correct by design.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running Codex in main context | Always use a subagent via Agent tool |
| Forgetting `--json` on round 1 | You need the JSON output to capture the thread_id |
| Forgetting `2>/dev/null` | Codex thinking tokens flood context |
| Forgetting `-o` flag | Output mixes with metadata noise |
| Using `codex exec` instead of `codex exec resume` on round 2+ | Without resume, Codex starts fresh with no memory of prior feedback |
| Not updating `/tmp/codex-review-content.md` between rounds | Codex re-reads the file — if you don't update it, it reviews the same content |
| Looping beyond 3 rounds | Diminishing returns; surface to user instead |
| Trusting Codex blindly on final findings | Always validate persistent findings against project context |
| Hardcoding model | Let the user's codex config choose the model |

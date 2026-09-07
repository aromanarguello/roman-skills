---
name: final-review
description: "Review a completed change before merge, covering quality, maintainability, security, regression, performance, and applicable data-integrity or mobile concerns. Use for final review, pre-merge review, or run all reviews; accepts selected concerns. Honor review-only requests and repair supported findings when authorized."
---

# Final Review

Review the task-owned change, combine evidence-backed findings, and verify authorized fixes against the final content. This skill is **model-agnostic**: model/provider choice, effort, and specialized profiles belong to the user or host configuration.

Read [the review contract](references/review-contract.md) before starting. It defines source selection, scope, review criteria, result format, completion gates, and the repair loop. Keep this whole skill directory together when installing it; its resources have no dependency on another skill installation or a personal configuration.

## Arguments

Use the arguments supplied by the host (`$ARGUMENTS` where supported), or the concerns named in the user's request:

- `pr-review`: correctness, tests, errors, types and maintainability.
- `structural-quality` (alias `thermo`): semantic branching, ownership boundaries and unnecessary concepts.
- `techdebt`: duplication, dead code and over-abstraction.
- `security`: exploitable trust-boundary and authorization defects.
- `regression`: consumer impact, compatibility and missing path coverage.
- `performance`: evidenced hot-path, query, payload and resource costs.
- `data-integrity`: persistence, migrations, isolation and transactional correctness.
- `react-native`: relevant mobile runtime, UI and native configuration risks.
- `all` or no arguments: all general sources, plus applicable data-integrity/mobile sources.

An explicitly named conditional source always runs. For example, `final-review security data-integrity` reviews those two concerns even when path heuristics would not select persistence work.

## Host-independent dispatch

Build only nonempty jobs from the selected sources:

| Job | Sources |
| --- | --- |
| quality | pr-review, structural-quality, techdebt |
| risk | security, data-integrity |
| regression-performance | regression, performance |
| mobile | react-native |

Use the current host's actual delegation interface. Do not assume an `Agent`, `Task`, or `spawn_agent` function exists just because another host exposes it. Read the available tool schema and translate each job into supported arguments:

- Select an available read-only reviewer role, or constrain a suitable general-purpose worker to read-only inspection. Pass the actual role/profile selector when one exists; naming a profile in prompt text does not select it. Do not require named private profiles.
- Use the user's configured model/effort or an explicitly requested override through actual supported controls. Do not invent model IDs or claim a selection the tool did not apply. A missing explicit model/expertise requirement is a coverage gap; an unreported default is not proof of a requested override.
- Give each reviewer a fresh context when supported and a self-contained packet from the review contract: objective, repository, base/HEAD, final snapshot, selected sources, applicable instructions and expected output. Reviewers must not delegate further.
- Start independent jobs before waiting, using background/task handles when supported. Keep at most four active reviewers, respect lower environment limits, and account for other active work. Use unique job/run identifiers across repair rounds.
- Collect final results with bounded waits and report progress. Missing, failed, timed-out or incomplete jobs remain visible as coverage gaps. Stop stalled readers before editing; use cleanup controls only when exposed.

When delegation is unavailable, perform the selected concerns sequentially in the current agent and disclose that the review was local rather than independent. Local review can be complete if the requested coverage is satisfied; it cannot satisfy an explicit requirement for independent reviewers or a model/capability that is unavailable.

## Bundled verification

The [scope helper](scripts/review_scope.py) records explicitly owned committed and working-tree changes against a verified base. The [result gate](scripts/review_gate.py) rejects incomplete, stale or malformed coverage while retaining valid findings. Both require Python 3.9 or newer and the standard library; scope capture also requires Git. See the review contract for inputs, invocation and limitations.

Run the portable helper regression suite from a checkout of this repository:

```bash
python3 -m unittest discover -s final-review/tests -v
```

The helpers validate artifacts and declared status; the parent still owns source selection, finding adjudication, routing evidence and applicable checks. If a helper cannot run, use an equivalent explicit verification and state that limitation. Never turn missing verification into an empty approved review.

Finish with `REVIEW_PASSED`, `FINDINGS_OPEN`, or `REVIEW_INCOMPLETE` for the actual final snapshot. Follow the shared contract's verified repair loop when edits are authorized; a passing review does not authorize staging, commits, pushing, merging, deployment or messages.

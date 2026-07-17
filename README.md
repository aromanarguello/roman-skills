# roman-skills

Open source skills for better AI-assisted development in [Claude Code](https://claude.ai/code) and Codex.

## Skills

### [coding-guidelines](./coding-guidelines/SKILL.md)

Behavioral guidelines to reduce common LLM coding mistakes, based on Karpathy's principles. Covers four areas:

1. **Think Before Coding** - Surface assumptions and tradeoffs before writing code
2. **Simplicity First** - Minimum code that solves the problem
3. **Surgical Changes** - Touch only what you must
4. **Goal-Driven Execution** - Define verifiable success criteria

### [grill-me](./grill-me/SKILL.md)

Opinionated sparring partner for sharpening ideas, plans, features, architecture, strategy, and creative projects before committing to a direction.

- Forces one decision at a time with the agent's recommended answer first
- Walks through the GRILL sequence: Ground, Refine, Investigate, Link, Land
- Uses concrete examples, decision tables, and diagrams when ideas get abstract
- Lands with a concise action plan that can become a ticket, brief, or implementation plan

### [techdebt](./techdebt/SKILL.md)

Find and eliminate duplicated code, dead code, and unnecessary abstractions. Run at end of coding sessions or when the codebase feels cluttered.

- Scans for duplications, dead code, and over-abstractions
- Presents findings grouped by severity with file:line references
- Interactive cleanup with regression verification

### [parallel-subagents](./parallel-subagents/SKILL.md)

Orchestrate 2+ independent tasks in parallel for research, quick tasks, or test execution.

- Three modes: Research (Explore agents), Quick tasks (general-purpose), Testing
- Decision tree for choosing the right parallelism skill
- Templates and examples for each mode

### [codex](./codex/SKILL.md)

Delegate one-shot tasks to OpenAI Codex CLI via a Bash subagent. Routes between `codex review` for review requests and `codex exec` (read-only by default) for everything else.

- Subagent dispatch keeps Codex output isolated from main context
- Quick reference table mapping user phrasing to flags
- Write access requires explicit user request (`workspace-write`)

### [codex-audit](./codex-audit/SKILL.md)

Deep code audit via Codex CLI with full repo access, then a mandatory validation gate where Claude cross-checks every finding against actual source and project docs before presenting.

- `--full-auto` with `danger-full-access` so Codex can run tests and explore
- Per-finding validation classifies results as Confirmed or Likely False Positive
- Designed to filter out Codex hallucinations and intentional-design misreads

### [codex-iterative](./codex-iterative/SKILL.md)

Multi-round iterative review via Codex CLI with session resumption. Codex reviews a plan, design, or diff, returns a verdict (APPROVED/REVISE), and Claude fixes issues and resubmits until Codex approves.

- Up to 3 rounds with `codex exec resume` so Codex remembers prior feedback
- Subagent dispatch keeps Codex output isolated from main context
- Final-round validation against project context to filter Codex misunderstandings

### [orchestrate-lane](./orchestrate-lane/SKILL.md)

Codex-specific manager-thread workflow for splitting work into accountable lane threads with goals, acceptance criteria, review gates, PR babysitting, and wrap-up.

- Defines the manager thread, lane thread, lane contract, heartbeat/check-in, review gate, and wrap-up primitives
- Includes templates for existing-work and new-work lane handoffs
- Keeps PRs moving through tests, CI, review-bot comments, and merge readiness

### [final-review](./final-review/SKILL.md)

Pre-merge review that runs PR quality, tech debt, security, regression, and performance analysis in parallel via background general-purpose agents, aggregates findings into a unified prioritized report, then auto-fixes mechanical issues.

- Single-message parallel dispatch for true concurrency
- Inlined criteria per concern — no dependency on private subagents
- Auto-fix gate for mechanical findings; pauses only on genuine ambiguity

## Usage

Add a skill to your project by copying the file into `.claude/skills/` in your repository, or symlink it from a shared location.

## License

MIT

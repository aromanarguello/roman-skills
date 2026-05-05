# roman-skills

Open source [Claude Code](https://claude.ai/code) skills for better AI-assisted development.

## Skills

### [coding-guidelines](./coding-guidelines/SKILL.md)

Behavioral guidelines to reduce common LLM coding mistakes, based on Karpathy's principles. Covers four areas:

1. **Think Before Coding** - Surface assumptions and tradeoffs before writing code
2. **Simplicity First** - Minimum code that solves the problem
3. **Surgical Changes** - Touch only what you must
4. **Goal-Driven Execution** - Define verifiable success criteria

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

## Usage

Add a skill to your project by copying the file into `.claude/skills/` in your repository, or symlink it from a shared location.

## License

MIT

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

## Usage

Add a skill to your project by copying the file into `.claude/skills/` in your repository, or symlink it from a shared location.

## License

MIT

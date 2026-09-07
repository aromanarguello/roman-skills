# Dispatch examples

Read only the example for the active host. These are tool-call examples, not shell scripts. Fill `reviewPacket` from the [review contract](review-contract.md): objective, acceptance criteria, repository and scope paths, base/HEAD/snapshot, selected sources, applicable instructions, read-only/no-delegation constraints, and the expected JSON result. The job ID inside that packet must match the parent's expectation map; use `mobile` for the job and `react-native` for its source.

Select an available reviewer using the user's or host's routing rules. The role/type variables below must contain actual catalog entries; this package requires no private profile or fixed model. A suitable general-purpose worker is a fallback only when its permitted capabilities and configured model satisfy the assignment. The packet still requires read-only review.

## Codex with collaboration tools

When the active schema exposes `collaboration.spawn_agent`, pass the selected role through `agent_type`. For example, `reviewerRole` may be `default` if that role is available and no more specific routing requirement applies:

```javascript
collaboration.spawn_agent({
  agent_type: reviewerRole,
  task_name: "final_review_quality_run_1_round_1",
  fork_turns: "none",
  message: reviewPacket
})
```

Use a unique task name for each selected job and repair round. Dispatch independent jobs before waiting. Collect their final answers through the host's completion notifications and supported wait/status tools; a mailbox notification alone is not a final result. Record the returned task handle and tool-confirmed routing. If an explicit model/effort override is required, supply it through supported fields rather than naming a model in the prompt. Other Codex runtimes may expose a different API; translate the call using their actual schemas.

## Claude Code with the Agent tool

Choose an available non-fork reviewer type. `reviewerType` can be `general-purpose` when that type is available and satisfies the routing requirements; prefer a suitable configured read-only reviewer when present. Supply the complete packet as `prompt`:

```javascript
Agent({
  subagent_type: reviewerType,
  description: "Review selected concerns",
  prompt: reviewPacket
})
```

Use a new invocation for each job and repair round. A `fork` type or resumed agent retains prior conversation context. In fork-enabled sessions, background execution is automatic and `run_in_background` is absent from the schema; pass that field only when the active schema exposes it. Wait for completed results using the host's supported notifications and task controls. Check the selected type's model configuration against any explicit requirement; these examples leave model choice to that configuration. See the official [Claude Code subagent documentation](https://code.claude.com/docs/en/sub-agents#turn-fork-mode-on-or-off).

For either host, save completed reviewer JSON and run the shared gate against the final snapshot. Missing routing, partial output, failed jobs, and unsupported capabilities remain coverage gaps as defined by the contract. If delegation is unavailable, use the sequential fallback in SKILL.md and disclose its limits.

# AutoSkillResearch Agent Optimization Strategy

## Hypothesis Space
Try these modification categories in rough priority order:

1. **Tool usage patterns** — Is the agent using its tools effectively? Try reordering tool calls, adjusting when to use which tool, or adding explicit tool selection criteria.
2. **Search query strategy** — For research agents: test different query formulation approaches, number of queries, query diversity requirements.
3. **Output structure** — Experiment with output format, section ordering, level of detail, and what gets included vs omitted.
4. **Constraint tuning** — Adjust hard limits (e.g., "max 3 Context7 calls") up or down. Test whether constraints help quality or just limit capability.
5. **Cross-referencing discipline** — How the agent validates and reconciles information from multiple sources. Test explicit vs implicit verification requirements.
6. **Role framing** — How the agent understands its purpose. Test specialist vs generalist framing, confidence calibration instructions.

## Anti-Patterns
- Do NOT remove source attribution requirements — agents must remain verifiable
- Do NOT remove tool usage constraints entirely — unconstrained agents waste tokens and produce noise
- Do NOT optimize for speed at the expense of accuracy — the agent's output feeds into the skill's final output
- Adding too many workflow steps rarely helps and inflates token cost

## Per-Iteration Protocol
1. Read the experiment log. Identify what's been tried and what hasn't.
2. Pick a hypothesis that targets the weakest eval cases.
3. Make ONE focused change to the agent file (not multiple changes per iteration).
4. Write a clear hypothesis before editing.
5. If the last 3 iterations were all discarded, try a fundamentally different approach.

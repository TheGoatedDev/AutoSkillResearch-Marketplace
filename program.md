# AutoSkillResearch Optimization Strategy

## Hypothesis Space
Try these modification categories in rough priority order:

1. **Instruction clarity** — Are instructions unambiguous? Try rephrasing vague directives.
2. **Example quality** — Add, remove, or modify examples. Test 0 vs 1 vs 3 examples.
3. **Structure** — Experiment with instruction ordering, grouping, and hierarchy.
4. **Constraint specificity** — Make implicit constraints explicit. Test hard rules vs soft guidance.
5. **Tone and framing** — Test authoritative vs collaborative vs neutral tone.
6. **Scope** — Is the skill trying to do too much? Try narrowing focus.

## Anti-Patterns
- Do NOT remove error handling sections even if they seem verbose
- Do NOT optimize for conciseness at the expense of completeness
- Adding more than 3 examples rarely helps and inflates token cost

## Per-Iteration Protocol
1. Read the experiment log. Identify what's been tried and what hasn't.
2. Pick a hypothesis that targets the weakest eval cases.
3. Make ONE focused change (not multiple changes per iteration).
4. Write a clear hypothesis before editing.
5. If the last 3 iterations were all discarded, try a fundamentally different approach.

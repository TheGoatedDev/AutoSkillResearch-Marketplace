# AutoSkillResearch

Self-improving Claude Code skills marketplace.

## Project Structure

- `plugins/` — Each subdirectory is a skill plugin with evals
- `scripts/` — Python scripts for deterministic bookkeeping (ELO, logs, changelog)
- `.claude/skills/autoresearch/` — The orchestrator skill
- `.claude/agents/` — Subagent definitions (executor, judge)
- `program.md` — Skill optimization strategy
- `program-agents.md` — Agent optimization strategy

## Running the Loop

Invoke `/autoresearch` to start the autonomous optimization loop.
Invoke `/autoresearch <skill-name>` to optimize a single skill.

## Adding a Skill

Copy `templates/plugin-scaffold/` to `plugins/<your-skill>/` and fill in the files.
A skill needs >=5 eval cases in `evals/cases.json` to participate in the autoresearch loop.

## Agent Optimization

Plugins can include agents in `plugins/<skill>/agents/`. To opt agents into the optimization loop, add an `optimizable_agents` array to `plugin.json` listing the agent filenames (e.g., `["researcher.md"]`). Agent optimization runs as a separate rotation after skill optimization, using per-target ELO/log state files (e.g., `elo-researcher.json`).

## Scripts

All scripts in `scripts/` are standalone CLI tools. They read/write JSON and print to stdout.
Run with: `python3 scripts/<script>.py --help`

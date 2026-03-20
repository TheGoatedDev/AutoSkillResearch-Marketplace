# AutoSkillResearch — Design Specification

**Date:** 2026-03-20
**Status:** Draft
**Author:** Thomas Burridge + Claude

## 1. Overview

AutoSkillResearch is a Claude Code marketplace where every skill is continuously self-improved by an autonomous agent loop. Inspired by Andrej Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) project, the system applies closed-loop hill-climbing optimization to Claude Code skill content.

The core loop: an orchestrator agent reads a skill, hypothesizes a modification, evaluates the modified skill head-to-head against the current version via ELO-style ranking, and keeps or discards the change. This runs autonomously overnight on a Claude Code Max subscription (Sonnet).

### Goals

- A monorepo marketplace of Claude Code skills, installable as a standard Claude Code marketplace
- Every skill with eval cases participates in an autonomous self-improvement loop
- Users can contribute new eval cases (failure reports) that feed into subsequent optimization runs
- Skills auto-update with generated changelogs; users can roll back

### Non-Goals (v1)

- Cross-skill regression testing (deferred until usage data reveals real conflicts)
- Passive usage-signal collection (accept/reject tracking)
- Direct user steering of the optimization loop via constraints
- Distributed/multi-machine optimization

## 2. Architecture

### 2.1 Repository Structure

```
AutoSkillResearch/
├── .claude-plugin/
│   └── marketplace.json               # Makes this repo a Claude Code marketplace
├── .claude/
│   ├── settings.local.json            # Auto-permissions for eval/git operations
│   ├── skills/
│   │   └── autoresearch/
│   │       └── SKILL.md               # Orchestrator skill (/autoresearch)
│   └── agents/
│       ├── skill-optimizer.md          # Proposes SKILL.md modifications
│       ├── skill-executor.md          # Runs a skill against one eval case
│       └── skill-judge.md             # ELO head-to-head comparison judge
├── CLAUDE.md                           # Project instructions for Claude Code
├── program.md                          # Global optimization strategy
├── plugins/
│   ├── <skill-name>/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json            # Plugin metadata (name, description, author)
│   │   ├── skills/
│   │   │   └── <skill-name>/
│   │   │       └── SKILL.md           # The skill content (what gets optimized)
│   │   ├── evals/
│   │   │   ├── cases.json             # Eval cases: input, context, rubric
│   │   │   └── config.json            # Tolerance bands, metric thresholds
│   │   ├── optimize.md                # Optional per-skill strategy overrides
│   │   └── experiments/
│   │       ├── log.json               # Structured experiment log (capped at 50)
│   │       ├── elo.json               # ELO ratings per version
│   │       └── changelog.md           # Auto-generated changelog
│   └── ...
├── templates/
│   ├── eval-case.json                 # Template for contributing eval cases
│   └── plugin-scaffold/               # Scaffold for new plugin directory
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── SKILL.md
│       └── evals/
│           ├── cases.json
│           └── config.json
└── scripts/                            # Core autoresearch engine
    ├── autoresearch.py                 # Main loop controller
    ├── eval_runner.py                  # Executes skill against eval cases via claude CLI
    ├── elo.py                          # ELO rating tracker
    ├── experiment_log.py               # Log management + FIFO pruning
    └── changelog.py                    # Generates changelog from experiment history
```

### 2.2 Marketplace Integration

The repo is a standard Claude Code marketplace. Users install it via:

```bash
claude plugin marketplace add <github-user>/AutoSkillResearch
```

**`.claude-plugin/marketplace.json`:**
```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "autoskillresearch",
  "description": "Self-improving Claude Code skills marketplace — skills that get better overnight",
  "owner": {
    "name": "Thomas Burridge",
    "email": "<email>"
  },
  "plugins": [
    {
      "name": "<skill-name>",
      "description": "<skill description>",
      "source": "./plugins/<skill-name>",
      "category": "<category>"
    }
  ]
}
```

Each plugin under `plugins/` follows the standard `.claude-plugin/plugin.json` format and is independently installable.

### 2.3 Tiered Acceptance

Skills in the marketplace exist in two tiers:

| Tier | Requirements | Autoresearch | Installable |
|------|-------------|--------------|-------------|
| **Standard** | `plugin.json` + `SKILL.md` | No | Yes |
| **Optimized** | Standard + `evals/cases.json` with ≥5 cases | Yes | Yes |

Only skills with eval cases participate in the autoresearch loop. Skills without evals are browsable and installable but static.

## 3. The Autoresearch Loop

### 3.1 Overview

A single orchestrator agent (invoked via `/autoresearch`) runs the entire loop. It processes one skill at a time, sequentially.

```
READ CONTEXT → HYPOTHESIZE & MODIFY → EVALUATE (ELO MATCH) → KEEP/DISCARD → LOOP
```

The loop runs until interrupted by the human, mirroring Karpathy's "do NOT pause to ask" directive.

### 3.2 Step-by-Step

**Step 1: Read Context**
The orchestrator reads:
- `program.md` — global optimization strategy
- `plugins/<skill>/optimize.md` — per-skill strategy overrides (if present)
- `plugins/<skill>/experiments/log.json` — what's been tried, what worked/failed
- `plugins/<skill>/skills/<skill>/SKILL.md` — current skill content
- `plugins/<skill>/evals/cases.json` — eval case definitions
- `plugins/<skill>/evals/config.json` — metric configuration

**Step 2: Hypothesize & Modify**
Based on context, the orchestrator:
1. Forms a hypothesis (e.g., "Adding explicit error handling instructions will improve eval quality")
2. Reads the current SKILL.md content and saves it in memory as `champion_content`
3. Edits the SKILL.md file
4. Commits the change to git on the working branch `autoresearch/<skill-name>`

The orchestrator works on a single persistent branch per skill (`autoresearch/<skill-name>`), not a new branch per iteration.

**Step 3: Evaluate (ELO Match)**

For each eval case in `cases.json`:

*3a. Trigger test:*
1. Run `claude -p "<eval input>" --output-format stream-json` with the modified skill loaded
2. Check if the skill was invoked (via stream event detection)
3. Compare actual trigger behavior against `expected_trigger` field
4. Record trigger hit/miss for `trigger_accuracy` metric

*3b. Quality test (only for cases where `expected_trigger: true`):*
1. Run the **champion** skill content against the eval case input → `output_old` (orchestrator passes saved `champion_content` as the skill text to the executor agent)
2. Run the **candidate** (modified) skill content against the same input → `output_new`
3. Present both outputs (randomized order, anonymized as "Response A"/"Response B") to the judge agent along with the rubric
4. Judge picks a winner or declares a draw
5. Update ELO ratings
6. Count tokens in both outputs for `token_efficiency` metric

Execution uses subagents dispatched by the orchestrator:
- `skill-executor` agent: receives skill content + eval case input, executes the skill in a forked context, returns the output text + token count
- `skill-judge` agent: receives two anonymized outputs + rubric, returns `{"winner": "A"|"B"|"draw", "reasoning": "..."}`

The orchestrator passes the champion SKILL.md content directly to the executor agent (read into memory before modification), avoiding the need to check out different git commits.

**Step 4: Keep / Discard**
Apply the promotion decision tree (see Section 5.2):
1. Minimum matches gate
2. Hard floor check on all metrics
3. ELO confidence check
4. Pareto tolerance band check

On **KEEP**: update `log.json`, update `elo.json`, bump patch version in `plugin.json`, update `changelog.md`. The modified SKILL.md becomes the new champion.
On **DISCARD**: `git reset --hard HEAD~1` on the working branch (reverts the candidate commit). Update `log.json` with the failed attempt (log update is committed separately).

**Step 5: Loop**
Return to Step 1 with the next hypothesis. Exit conditions (checked in order):
1. **Fixed iteration count reached** (`iterations_per_rotation`, default 10) → move to next skill
2. **All metrics at ceiling** (eval_quality ≥ 0.95, trigger_accuracy ≥ 0.95) → move to next skill early

### 3.3 Skill Rotation

The orchestrator processes skills round-robin:
1. List all "Optimized" tier skills (those with eval cases)
2. For each skill, run N iterations (configurable, default 10)
3. Move to next skill
4. After completing a full rotation, start over

This prevents one skill from monopolizing the loop.

## 4. Eval System

### 4.1 Eval Case Format

```json
[
  {
    "id": "unique-case-id",
    "input": "The user prompt that triggers the skill",
    "expected_trigger": true,
    "context": {
      "files": ["optional-list-of-files-in-working-dir"],
      "description": "Description of the project/environment context"
    },
    "rubric": "Plain-English description of what a good response looks like. Used by the judge agent to pick a winner in head-to-head comparison.",
    "metrics": ["eval_quality"]
  }
]
```

**Required fields:** `id`, `input`, `rubric`
**Optional fields:** `context`, `metrics` (defaults to `["eval_quality"]`), `expected_trigger` (defaults to `true`)

Eval cases with `"expected_trigger": false` are negative cases — they test that the skill does NOT trigger for irrelevant inputs. For negative cases, only `trigger_accuracy` is measured (no output to judge).

Context files referenced in `context.files` must be checked into the repo under `plugins/<skill-name>/evals/fixtures/`. Entries in the `files` array are paths **relative to the fixtures directory** (e.g., `["Dockerfile", "src/index.ts"]` resolves to `plugins/<skill-name>/evals/fixtures/Dockerfile`). If a referenced file is missing at eval time, the eval case is skipped with a warning logged.

### 4.2 Metric Types

| Metric | What It Measures | How It's Measured | Scale |
|--------|-----------------|-------------------|-------|
| `eval_quality` | Does the skill produce good output for this input? | Win rate: proportion of eval cases where the candidate beats the champion in head-to-head judging. Draws count as 0.5. | 0.0–1.0 |
| `trigger_accuracy` | Does the skill trigger when it should (and not when it shouldn't)? | Accuracy: proportion of eval cases where trigger behavior matches `expected_trigger`. | 0.0–1.0 |
| `token_efficiency` | How concise is the skill's output relative to baseline? | Ratio: `champion_avg_tokens / candidate_avg_tokens`. Normalized via `min(ratio, 2.0) / 2.0`. Neutral point is **0.5** (no change). Values > 0.5 mean the candidate is more concise; < 0.5 means more verbose. | 0.0–1.0 |

All metrics are normalized to a 0.0–1.0 scale so tolerance bands and minimums are comparable across metrics.

### 4.3 Eval Config

```json
{
  "metrics": {
    "eval_quality": {
      "tolerance": 0.02,
      "minimum": 0.6
    },
    "trigger_accuracy": {
      "tolerance": 0.05,
      "minimum": 0.7
    },
    "token_efficiency": {
      "tolerance": 0.10,
      "minimum": null
    }
  },
  "iterations_per_rotation": 10,
  "elo_confidence_threshold": 1520,
  "elo_minimum_matches": 5
}
```

## 5. ELO Ranking System

### 5.1 Design

Each skill version has an ELO rating. When the orchestrator produces a new candidate version, it plays "matches" against the current champion.

- **Starting ELO:** 1500 for every new version
- **K-factor:** 32
- **Win:** Judge picks this version's output as better → ELO gain
- **Loss:** Judge picks the other version → ELO loss
- **Draw:** Judge declares tie → small ELO adjustment toward 1500

### 5.2 Promotion Decision Tree

A candidate is evaluated after all eval cases in the current iteration have been played as matches. The decision follows this exact sequence:

1. **Minimum matches gate:** Has the candidate played at least `elo_minimum_matches` matches? Since the Optimized tier requires ≥5 eval cases and each case is one match, this gate always passes on the first iteration. It exists as a safety net if the minimum eval case requirement is lowered in the future.

2. **Hard floor check:** Compute each metric as a 0-1 score (see Section 4.2). If any metric with a non-null `minimum` is below that floor → **DISCARD**.

3. **ELO confidence check:** Is the candidate's ELO ≥ `elo_confidence_threshold` (default 1520)? If not → **DISCARD**.

4. **Pareto tolerance check:** For every metric that regressed (new < old), is the regression ≤ `tolerance`? AND did at least one metric improve? If both conditions hold → **KEEP**. Otherwise → **DISCARD**.

All four checks must pass for promotion. ELO resets to 1500 for each new candidate (each iteration starts fresh). Metrics with `"minimum": null` skip the hard floor check.

### 5.3 ELO State File

```json
{
  "current_champion": {
    "commit": "a1b2c3d",
    "elo": 1548,
    "matches_played": 12,
    "promoted_at": "2026-03-20T22:30:00Z"
  },
  "candidate": {
    "commit": "e4f5g6h",
    "elo": 1512,
    "matches_played": 7
  },
  "history": [
    {
      "commit": "0001abc",
      "final_elo": 1500,
      "outcome": "initial"
    },
    {
      "commit": "a1b2c3d",
      "final_elo": 1548,
      "outcome": "promoted"
    }
  ]
}
```

## 6. Agent Definitions

### 6.1 Orchestrator Skill (`/autoresearch`)

The entry point. Invoked by the user as `/autoresearch` or `/autoresearch <skill-name>`.

**Responsibilities:**
- Read global and per-skill strategy
- Select the next skill to optimize
- Read experiment history and form hypotheses
- Edit SKILL.md files
- Dispatch executor and judge subagents
- Interpret results and make keep/discard decisions
- Manage git commits and reverts
- Update experiment logs, ELO state, and changelogs

**Context management:** The orchestrator resets context between skills by reading fresh state from disk (log.json, SKILL.md, etc.) rather than accumulating in-memory state.

### 6.2 Skill Executor Agent

A subagent that executes a skill against an eval case.

**Input:**
- `skill_content`: The full SKILL.md text (either champion or candidate version)
- `eval_input`: The user prompt from the eval case
- `eval_context`: Optional context (file descriptions, environment)

**Execution mechanism:** The orchestrator writes a temporary SKILL.md to a temp directory, then invokes `claude -p "<eval_input>" --output-format stream-json` with the skill loaded from that temp path. The executor captures the full output and token count, then cleans up the temp skill file.

**Output:** `{"output": "<full response text>", "token_count": 1234, "triggered": true}`
**Isolation:** Runs in a forked context (`context: fork`) so the skill executes cleanly without contamination from the orchestrator's state.

### 6.3 Skill Judge Agent

A subagent that performs head-to-head comparison.

**Input:** Two anonymized responses (A and B) + the eval case rubric
**Output:** `{"winner": "A" | "B" | "draw", "reasoning": "..."}`
**Isolation:** Runs in a forked context. Does not know which response is old vs new.

## 7. Experiment Log

### 7.1 Entry Format

```json
{
  "iteration": 1,
  "timestamp": "2026-03-20T22:15:00Z",
  "commit": "a1b2c3d",
  "hypothesis": "Adding explicit step numbering will improve instruction following",
  "change_summary": "Converted bullet points to numbered steps in SKILL.md",
  "metrics": {
    "eval_quality": { "old": 0.72, "new": 0.78, "delta": 0.06 },
    "trigger_accuracy": { "old": 0.85, "new": 0.84, "delta": -0.01 },
    "token_efficiency": { "old": 0.55, "new": 0.58, "delta": 0.03 }
  },
  "elo": { "starting": 1500, "final": 1528, "matches": 8, "wins": 5, "losses": 2, "draws": 1 },
  "outcome": "kept",
  "lessons": "Numbered steps improved output structure without hurting trigger accuracy"
}
```

**Field definitions:**
- `metrics.*`: All values are on the 0.0–1.0 scale defined in Section 4.2
  - `eval_quality`: win rate (wins + 0.5×draws) / total matches
  - `trigger_accuracy`: correct trigger predictions / total eval cases
  - `token_efficiency`: normalized ratio (see Section 4.2)
- `elo`: the candidate's ELO journey for this iteration
- `outcome`: one of `"kept"`, `"discarded"`, `"error"`
```

### 7.2 Pruning Strategy

- **Cap:** 50 discarded entries maximum (FIFO — oldest discarded entries removed first when cap is exceeded)
- **Kept entries:** Uncapped, persist indefinitely. If kept entries exceed 30, the oldest kept entries are summarized into a `lessons_summary` field at the top of the log (one-line-per-entry digest) and the detailed entries are removed.
- **Rationale:** The history of what worked is more valuable for building on success. The history of what failed prevents repeat mistakes, but recent failures are more relevant than old ones.

## 8. Optimization Strategy (program.md)

### 8.1 Global Strategy

`program.md` at the repo root provides the default optimization strategy for all skills. It guides the orchestrator's hypothesis generation.

Example content:
```markdown
# AutoSkillResearch Optimization Strategy

## Hypothesis Space
Try these modification categories in rough priority order:

1. **Instruction clarity** — Are instructions unambiguous? Try rephrasing vague directives.
2. **Example quality** — Add, remove, or modify examples. Test 0 vs 1 vs 3 examples.
3. **Structure** — Experiment with instruction ordering, grouping, and hierarchy.
4. **Constraint specificity** — Make implicit constraints explicit. Test hard rules vs soft guidance.
5. **Tone and framing** — Test authoritative vs collaborative vs neutral tone.
6. **Scope** — Is the skill trying to do too much? Try narrowing focus.

## Anti-Patterns (learned)
- Do NOT remove error handling sections even if they seem verbose
- Do NOT optimize for conciseness at the expense of completeness
- Adding more than 3 examples rarely helps and inflates token cost

## Per-Iteration Protocol
1. Read the experiment log. Identify what's been tried and what hasn't.
2. Pick a hypothesis that targets the weakest eval cases.
3. Make ONE focused change (not multiple changes per iteration).
4. Write a clear hypothesis before editing.
```

### 8.2 Per-Skill Overrides

Individual skills can provide `optimize.md` to add constraints or focus areas:

```markdown
# Optimization Notes for deploy-helper

## Focus Areas
- Users report the skill suggests SSH when Docker is available. Prioritize this.
- Trigger accuracy is already good (0.92). Focus on eval quality.

## Constraints
- Must always check for Dockerfile before suggesting alternatives.
- Keep the "safety checklist" section — users rely on it.
```

The orchestrator reads both `program.md` and `optimize.md`, with per-skill overrides taking precedence.

## 9. User Feedback

### 9.1 Eval Case Contribution

Users submit new eval cases by adding entries to `plugins/<skill-name>/evals/cases.json` via pull request.

**Template (`templates/eval-case.json`):**
```json
{
  "id": "descriptive-id",
  "input": "The exact prompt where the skill failed or underperformed",
  "context": {
    "files": [],
    "description": "Describe your project setup"
  },
  "rubric": "What should the skill have done? Be specific.",
  "metrics": ["eval_quality"]
}
```

**Process:**
1. User encounters a skill failure in real use
2. User forks the repo, adds an eval case entry
3. Submits a PR with a description of the failure
4. Maintainer reviews and merges
5. Next autoresearch run picks up the new case automatically

### 9.2 No Special Infrastructure

Feedback flows through standard git/GitHub mechanisms. No database, no API, no telemetry. The eval cases file IS the feedback store.

## 10. Versioning & Updates

### 10.1 Version Bumps

Each "kept" change bumps the patch version in the skill's `plugin.json`:
- `1.0.0` → `1.0.1` → `1.0.2` → ...

Major/minor bumps are manual (reserved for human-authored changes or significant shifts).

### 10.2 Changelog Generation

`changelog.md` is auto-generated from kept entries in `log.json`:

```markdown
# Changelog — deploy-helper

## v1.0.3 (2026-03-21)
- Improved: Added explicit Dockerfile detection before suggesting alternatives
  (eval_quality: 0.78 → 0.84)

## v1.0.2 (2026-03-20)
- Improved: Converted instructions to numbered steps
  (eval_quality: 0.72 → 0.78)

## v1.0.1 (2026-03-20)
- Improved: Added example for multi-stage Docker builds
  (eval_quality: 0.65 → 0.72)
```

### 10.3 User Updates

Users receive updates when they run `claude plugin update`. The marketplace tracks versions via git commits and `plugin.json` version fields.

Rollback: users can pin a specific version by checking out a tagged commit.

## 11. Compute Model

- **Runtime:** Claude Code Max subscription (unlimited Sonnet)
- **Rate limit management:** Sequential skill processing, one eval case at a time. No parallel subagent swarms.
- **Expected throughput:** ~3-5 iterations per hour per skill (each iteration involves 2×N eval executions + N judge calls, where N = number of eval cases)
- **Overnight run (10 hours):** ~30-50 iterations per skill, or ~5-10 iterations each across 5-10 skills in rotation

## 12. Error Handling & Crash Recovery

### 12.1 Subagent Failures

If any subagent call (executor or judge) fails or times out:
1. Log the failure in `log.json` with `"outcome": "error"` and the error message
2. Discard the current iteration (revert the candidate commit)
3. Continue to the next iteration

A single eval case failure does not abort the entire iteration. If ≥50% of eval cases error, the iteration is aborted.

### 12.2 Rate Limit Handling

On rate limit errors from the Claude API:
1. Wait 60 seconds
2. Retry the failed subagent call (max 3 retries)
3. If all retries fail, treat as a subagent failure (see above)

### 12.3 Git Failures

If a git operation fails (dirty working tree, merge conflict):
1. Log the error
2. Run `git stash` to save any uncommitted changes
3. Reset the working branch to the last known-good commit
4. Continue to the next iteration

### 12.4 Crash Recovery

If the orchestrator session crashes mid-run:
1. The user re-invokes `/autoresearch`
2. The orchestrator reads `log.json` and `elo.json` to determine where it left off
3. If an uncommitted modification exists (dirty working tree), it is discarded
4. The loop resumes from the next iteration

State is always persisted to disk (log.json, elo.json, git commits) before the next iteration begins. No in-memory-only state spans iterations.

### 12.5 Concurrency Guard

On start, the orchestrator creates `.autoresearch.lock` in the repo root containing:
```json
{"pid": 12345, "started_at": "2026-03-20T22:00:00Z", "skill": "deploy-helper"}
```

If the file exists and `started_at` is less than 4 hours old, the orchestrator refuses to start and prints a message. If the lock is stale (>4 hours), it is overwritten. The orchestrator refreshes the lock timestamp every 30 minutes during a run. The lock is deleted on clean exit.

## 13. Script / Agent Boundary

Python scripts handle **mechanical, deterministic operations:**
- `elo.py` — ELO math (compute new ratings from match outcomes)
- `experiment_log.py` — log CRUD, pruning, cap enforcement
- `changelog.py` — generate changelog from kept log entries

The orchestrator agent handles **creative, judgment-based operations:**
- Hypothesis generation (what to try next)
- SKILL.md modification (how to implement the hypothesis)
- Dispatching executor and judge subagents
- Interpreting results and writing lessons learned

The orchestrator calls Python scripts via the Bash tool for bookkeeping. Scripts read/write JSON files and print results to stdout. Scripts never call the Claude API.

## 14. Acknowledged Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| ELO convergence is slow | Medium | Accept slower promotion; 5-match minimum prevents premature decisions |
| Experiment log loses signal at high iteration counts | Medium | Cap at 50 entries; kept entries persist; agent reads fresh state each iteration |
| No cross-skill testing | Medium | Defer to v2; users report conflicts via eval case PRs |
| Auto-updates may disrupt users | Low | Changelog + rollback via version pinning |
| Agent retries same failed approaches | Medium | Experiment log tracks failed hypotheses; global strategy documents anti-patterns |
| Skill plateaus with no further improvement | Low | Natural stopping — ELO stabilizes, agent moves to next skill |
| LLM judge non-determinism | Medium | ELO absorbs noise over multiple matches; 5-match minimum |

## 15. Future Directions (out of scope for v1)

- **Cross-skill regression suite** — test common skill combinations before publishing
- **Passive usage signals** — track accept/reject/edit patterns from real users
- **Direct steering** — users add constraints to the optimization config
- **Veto/staging gate** — human review before publishing improved versions
- **Auto-evolving strategy** — `program.md` updates itself based on aggregate learnings
- **Multi-machine distribution** — SETI@home-style distributed optimization
- **Skill generation** — agent creates entirely new skills, not just improves existing ones

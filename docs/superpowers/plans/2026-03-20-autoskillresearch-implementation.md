# AutoSkillResearch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code marketplace with an autonomous autoresearch loop that iteratively improves skills via ELO-ranked head-to-head evaluation.

**Architecture:** Monorepo marketplace (`plugins/` directory of skills) with Python scripts for deterministic bookkeeping (ELO math, log management, changelog) and Claude Code agents/skills for creative work (hypothesis generation, skill execution, judging). The `/autoresearch` skill is the entry point that orchestrates the full loop.

**Tech Stack:** Python 3.11+, Claude Code (agents, skills, `claude` CLI), Git

**Spec:** `docs/superpowers/specs/2026-03-20-autoskillresearch-design.md`

**Spec Deviations:**
- The spec lists `scripts/eval_runner.py` as a Python script. This plan delegates skill execution to the `skill-executor` agent instead, which handles the `claude` CLI interaction natively. The agent approach is more flexible (can adapt to CLI quirks) and avoids encoding complex stream-JSON parsing logic in a standalone script.

---

## File Map

### Python Scripts (`scripts/`)
| File | Responsibility |
|------|---------------|
| `scripts/elo.py` | ELO rating math: compute new ratings from match outcomes, read/write `elo.json` |
| `scripts/experiment_log.py` | Log CRUD: add entries, enforce caps, FIFO pruning, lessons summary |
| `scripts/changelog.py` | Generate `changelog.md` from kept entries in `log.json` |
| `scripts/version.py` | Bump patch version in `plugin.json` |
| `scripts/metrics.py` | Compute normalized metric scores (eval_quality, trigger_accuracy, token_efficiency) from raw match/trigger data |
| `scripts/promotion.py` | Promotion decision tree: minimum matches → hard floor → ELO confidence → Pareto tolerance |
| `scripts/lockfile.py` | Concurrency guard: create/check/refresh/delete `.autoresearch.lock` |

### Agent Definitions (`.claude/agents/`)
| File | Responsibility |
|------|---------------|
| `.claude/agents/skill-executor.md` | Subagent: executes a skill against one eval case, returns output + token count + trigger status |
| `.claude/agents/skill-judge.md` | Subagent: compares two anonymized outputs against a rubric, picks winner |

### Orchestrator Skill (`.claude/skills/autoresearch/`)
| File | Responsibility |
|------|---------------|
| `.claude/skills/autoresearch/SKILL.md` | The `/autoresearch` skill: orchestrates the full loop |

### Marketplace & Config
| File | Responsibility |
|------|---------------|
| `.claude-plugin/marketplace.json` | Marketplace registration |
| `.claude/settings.local.json` | Auto-permissions for Bash commands used by the loop |
| `CLAUDE.md` | Project instructions for Claude Code |
| `program.md` | Global optimization strategy |

### Templates
| File | Responsibility |
|------|---------------|
| `templates/eval-case.json` | Template for user-contributed eval cases |
| `templates/plugin-scaffold/.claude-plugin/plugin.json` | Scaffold plugin metadata |
| `templates/plugin-scaffold/skills/SKILL.md` | Scaffold skill file |
| `templates/plugin-scaffold/evals/cases.json` | Scaffold eval cases |
| `templates/plugin-scaffold/evals/config.json` | Scaffold eval config |
| `templates/plugin-scaffold/evals/fixtures/.gitkeep` | Scaffold fixtures directory for eval context files |

### Test Files (`tests/`)
| File | Responsibility |
|------|---------------|
| `tests/test_elo.py` | Tests for ELO math |
| `tests/test_experiment_log.py` | Tests for log CRUD and pruning |
| `tests/test_changelog.py` | Tests for changelog generation |
| `tests/test_metrics.py` | Tests for metric normalization |
| `tests/test_promotion.py` | Tests for promotion decision tree |
| `tests/test_lockfile.py` | Tests for concurrency guard |

### Example Plugin (for testing the loop end-to-end)
| File | Responsibility |
|------|---------------|
| `plugins/example-greeter/.claude-plugin/plugin.json` | Example plugin metadata |
| `plugins/example-greeter/skills/example-greeter/SKILL.md` | Simple greeting skill |
| `plugins/example-greeter/evals/cases.json` | 6 eval cases for the greeter |
| `plugins/example-greeter/evals/config.json` | Eval config with metric thresholds |
| `plugins/example-greeter/experiments/log.json` | Empty initial log |
| `plugins/example-greeter/experiments/elo.json` | Initial ELO state |
| `plugins/example-greeter/experiments/changelog.md` | Empty initial changelog |

---

## Task 1: Project Scaffolding & Marketplace Files

**Files:**
- Create: `.claude-plugin/marketplace.json`
- Create: `.claude/settings.local.json`
- Create: `CLAUDE.md`
- Create: `program.md`
- Create: `templates/eval-case.json`
- Create: `templates/plugin-scaffold/.claude-plugin/plugin.json`
- Create: `templates/plugin-scaffold/skills/SKILL.md`
- Create: `templates/plugin-scaffold/evals/cases.json`
- Create: `templates/plugin-scaffold/evals/config.json`
- Create: `pyproject.toml`

- [ ] **Step 0: Initialize git repo and create `tests/__init__.py`**

```bash
git init
```

Create `tests/__init__.py` (empty file) and `scripts/__init__.py` (empty file) for Python module resolution.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "autoskillresearch"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.claude-plugin/marketplace.json`**

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "autoskillresearch",
  "description": "Self-improving Claude Code skills marketplace — skills that get better overnight",
  "owner": {
    "name": "Thomas Burridge"
  },
  "plugins": []
}
```

The `plugins` array will be populated as skills are added.

- [ ] **Step 3: Create `.claude/settings.local.json`**

```json
{
  "permissions": {
    "allow": [
      "Bash(python3:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git branch:*)",
      "Bash(git checkout:*)",
      "Bash(git reset:*)",
      "Bash(git stash:*)",
      "Bash(git log:*)",
      "Bash(git diff:*)",
      "Bash(claude:*)"
    ]
  }
}
```

- [ ] **Step 4: Create `CLAUDE.md`**

```markdown
# AutoSkillResearch

Self-improving Claude Code skills marketplace.

## Project Structure

- `plugins/` — Each subdirectory is a skill plugin with evals
- `scripts/` — Python scripts for deterministic bookkeeping (ELO, logs, changelog)
- `.claude/skills/autoresearch/` — The orchestrator skill
- `.claude/agents/` — Subagent definitions (executor, judge)
- `program.md` — Global optimization strategy

## Running the Loop

Invoke `/autoresearch` to start the autonomous optimization loop.
Invoke `/autoresearch <skill-name>` to optimize a single skill.

## Adding a Skill

Copy `templates/plugin-scaffold/` to `plugins/<your-skill>/` and fill in the files.
A skill needs ≥5 eval cases in `evals/cases.json` to participate in the autoresearch loop.

## Scripts

All scripts in `scripts/` are standalone CLI tools. They read/write JSON and print to stdout.
Run with: `python3 scripts/<script>.py --help`
```

- [ ] **Step 5: Create `program.md`**

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
```

- [ ] **Step 6: Create template files**

`templates/eval-case.json`:
```json
{
  "id": "descriptive-id",
  "input": "The exact prompt where the skill failed or underperformed",
  "expected_trigger": true,
  "context": {
    "files": [],
    "description": "Describe your project setup"
  },
  "rubric": "What should the skill have done? Be specific.",
  "metrics": ["eval_quality"]
}
```

`templates/plugin-scaffold/.claude-plugin/plugin.json`:
```json
{
  "name": "SKILL_NAME",
  "description": "SKILL_DESCRIPTION"
}
```

`templates/plugin-scaffold/skills/SKILL.md`:
```markdown
---
name: SKILL_NAME
description: "Use when TRIGGER_CONDITION"
---

# SKILL_NAME

Instructions here.
```

`templates/plugin-scaffold/evals/cases.json`:
```json
[]
```

`templates/plugin-scaffold/evals/config.json`:
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

- [ ] **Step 7: Commit**

```bash
git add .claude-plugin/ .claude/settings.local.json CLAUDE.md program.md templates/ pyproject.toml scripts/__init__.py tests/__init__.py
git commit -m "feat: project scaffolding with marketplace, templates, and config"
```

---

## Task 2: ELO Rating System (`scripts/elo.py`)

**Files:**
- Create: `scripts/elo.py`
- Create: `tests/test_elo.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_elo.py
import json
import pytest
from pathlib import Path
from scripts.elo import compute_elo_update, update_elo_state, create_initial_elo_state


class TestComputeEloUpdate:
    def test_win_increases_rating(self):
        new_a, new_b = compute_elo_update(1500, 1500, "A", k=32)
        assert new_a > 1500
        assert new_b < 1500

    def test_loss_decreases_rating(self):
        new_a, new_b = compute_elo_update(1500, 1500, "B", k=32)
        assert new_a < 1500
        assert new_b > 1500

    def test_draw_stays_near_equal(self):
        new_a, new_b = compute_elo_update(1500, 1500, "draw", k=32)
        assert abs(new_a - 1500) < 1
        assert abs(new_b - 1500) < 1

    def test_underdog_win_larger_gain(self):
        # Lower-rated player wins -> bigger ELO gain
        gain_underdog, _ = compute_elo_update(1400, 1600, "A", k=32)
        gain_favorite, _ = compute_elo_update(1600, 1400, "A", k=32)
        assert (gain_underdog - 1400) > (gain_favorite - 1600)

    def test_symmetric(self):
        new_a, new_b = compute_elo_update(1500, 1500, "A", k=32)
        assert abs((new_a - 1500) + (new_b - 1500)) < 0.01  # zero-sum


class TestCreateInitialEloState:
    def test_creates_initial_state(self):
        state = create_initial_elo_state("abc1234")
        assert state["current_champion"]["commit"] == "abc1234"
        assert state["current_champion"]["elo"] == 1500
        assert state["current_champion"]["matches_played"] == 0
        assert state["history"] == []
        assert state["candidate"] is None


class TestUpdateEloState:
    def test_updates_candidate_after_match(self, tmp_path):
        elo_path = tmp_path / "elo.json"
        initial = create_initial_elo_state("champ01")
        elo_path.write_text(json.dumps(initial))

        result = update_elo_state(
            elo_path=elo_path,
            candidate_commit="cand001",
            match_result="A",  # candidate wins (A = candidate)
        )
        assert result["candidate"]["elo"] > 1500
        assert result["candidate"]["matches_played"] == 1

    def test_promotion_updates_champion(self, tmp_path):
        elo_path = tmp_path / "elo.json"
        state = create_initial_elo_state("champ01")
        state["candidate"] = {
            "commit": "cand001",
            "elo": 1530,
            "matches_played": 6,
        }
        elo_path.write_text(json.dumps(state))

        result = update_elo_state(
            elo_path=elo_path,
            candidate_commit="cand001",
            match_result="promote",
        )
        assert result["current_champion"]["commit"] == "cand001"
        assert result["candidate"] is None
        assert len(result["history"]) == 1

    def test_discard_clears_candidate(self, tmp_path):
        elo_path = tmp_path / "elo.json"
        state = create_initial_elo_state("champ01")
        state["candidate"] = {
            "commit": "cand001",
            "elo": 1490,
            "matches_played": 6,
        }
        elo_path.write_text(json.dumps(state))

        result = update_elo_state(
            elo_path=elo_path,
            candidate_commit="cand001",
            match_result="discard",
        )
        assert result["current_champion"]["commit"] == "champ01"
        assert result["candidate"] is None
        assert result["history"][-1]["outcome"] == "discarded"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_elo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.elo'`

- [ ] **Step 3: Create `scripts/__init__.py` and implement `scripts/elo.py`**

```python
# scripts/__init__.py
# (empty)
```

```python
# scripts/elo.py
"""ELO rating system for head-to-head skill comparisons."""

import json
from datetime import datetime, timezone
from pathlib import Path


def compute_elo_update(
    rating_a: float, rating_b: float, winner: str, k: int = 32
) -> tuple[float, float]:
    """Compute new ELO ratings after a match.

    Args:
        rating_a: Current rating of player A
        rating_b: Current rating of player B
        winner: "A", "B", or "draw"
        k: K-factor (volatility)

    Returns:
        Tuple of (new_rating_a, new_rating_b)
    """
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 - expected_a

    if winner == "A":
        score_a, score_b = 1.0, 0.0
    elif winner == "B":
        score_a, score_b = 0.0, 1.0
    else:  # draw
        score_a, score_b = 0.5, 0.5

    new_a = rating_a + k * (score_a - expected_a)
    new_b = rating_b + k * (score_b - expected_b)
    return new_a, new_b


def create_initial_elo_state(champion_commit: str) -> dict:
    """Create initial ELO state for a skill."""
    return {
        "current_champion": {
            "commit": champion_commit,
            "elo": 1500,
            "matches_played": 0,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        },
        "candidate": None,
        "history": [],
    }


def update_elo_state(
    elo_path: Path,
    candidate_commit: str,
    match_result: str,  # "A" (candidate wins), "B" (champion wins), "draw", "promote", "discard"
) -> dict:
    """Update ELO state after a match or promotion/discard decision.

    Returns the updated state dict and writes it to disk.
    """
    state = json.loads(elo_path.read_text())

    if match_result == "promote":
        candidate = state["candidate"]
        state["history"].append({
            "commit": candidate["commit"],
            "final_elo": candidate["elo"],
            "outcome": "promoted",
        })
        state["current_champion"] = {
            "commit": candidate["commit"],
            "elo": candidate["elo"],
            "matches_played": candidate["matches_played"],
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        }
        state["candidate"] = None

    elif match_result == "discard":
        candidate = state["candidate"]
        if candidate:
            state["history"].append({
                "commit": candidate["commit"],
                "final_elo": candidate["elo"],
                "outcome": "discarded",
            })
        state["candidate"] = None

    else:  # match result: A, B, or draw
        if state["candidate"] is None or state["candidate"]["commit"] != candidate_commit:
            state["candidate"] = {
                "commit": candidate_commit,
                "elo": 1500,
                "matches_played": 0,
            }

        champion_elo = state["current_champion"]["elo"]
        candidate_elo = state["candidate"]["elo"]

        new_candidate, new_champion = compute_elo_update(
            candidate_elo, champion_elo, match_result, k=32
        )

        state["candidate"]["elo"] = new_candidate
        state["candidate"]["matches_played"] += 1
        state["current_champion"]["elo"] = new_champion
        state["current_champion"]["matches_played"] += 1

    elo_path.write_text(json.dumps(state, indent=2))
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_elo.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/__init__.py scripts/elo.py tests/test_elo.py
git commit -m "feat: ELO rating system with compute, create, and update operations"
```

---

## Task 3: Metrics Computation (`scripts/metrics.py`)

**Files:**
- Create: `scripts/metrics.py`
- Create: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_metrics.py
from scripts.metrics import compute_eval_quality, compute_trigger_accuracy, compute_token_efficiency


class TestEvalQuality:
    def test_all_wins(self):
        matches = [{"winner": "candidate"}] * 5
        assert compute_eval_quality(matches) == 1.0

    def test_all_losses(self):
        matches = [{"winner": "champion"}] * 5
        assert compute_eval_quality(matches) == 0.0

    def test_draws_count_half(self):
        matches = [{"winner": "draw"}] * 4
        assert compute_eval_quality(matches) == 0.5

    def test_mixed(self):
        matches = [
            {"winner": "candidate"},
            {"winner": "champion"},
            {"winner": "draw"},
        ]
        # 1 + 0 + 0.5 = 1.5 / 3 = 0.5
        assert compute_eval_quality(matches) == 0.5

    def test_empty_returns_zero(self):
        assert compute_eval_quality([]) == 0.0


class TestTriggerAccuracy:
    def test_all_correct(self):
        cases = [
            {"expected_trigger": True, "actual_trigger": True},
            {"expected_trigger": False, "actual_trigger": False},
        ]
        assert compute_trigger_accuracy(cases) == 1.0

    def test_all_wrong(self):
        cases = [
            {"expected_trigger": True, "actual_trigger": False},
            {"expected_trigger": False, "actual_trigger": True},
        ]
        assert compute_trigger_accuracy(cases) == 0.0

    def test_mixed(self):
        cases = [
            {"expected_trigger": True, "actual_trigger": True},
            {"expected_trigger": True, "actual_trigger": False},
        ]
        assert compute_trigger_accuracy(cases) == 0.5

    def test_empty_returns_zero(self):
        assert compute_trigger_accuracy([]) == 0.0


class TestTokenEfficiency:
    def test_equal_tokens(self):
        # ratio = 100/100 = 1.0, normalized = min(1.0, 2.0)/2.0 = 0.5
        assert compute_token_efficiency(100, 100) == 0.5

    def test_candidate_more_concise(self):
        # ratio = 200/100 = 2.0, normalized = min(2.0, 2.0)/2.0 = 1.0
        assert compute_token_efficiency(200, 100) == 1.0

    def test_candidate_more_verbose(self):
        # ratio = 100/200 = 0.5, normalized = min(0.5, 2.0)/2.0 = 0.25
        assert compute_token_efficiency(100, 200) == 0.25

    def test_candidate_extremely_concise(self):
        # ratio = 1000/100 = 10.0, capped at 2.0, normalized = 1.0
        assert compute_token_efficiency(1000, 100) == 1.0

    def test_zero_candidate_tokens_returns_neutral(self):
        assert compute_token_efficiency(100, 0) == 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_metrics.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `scripts/metrics.py`**

```python
# scripts/metrics.py
"""Compute normalized metrics from raw eval data."""


def compute_eval_quality(matches: list[dict]) -> float:
    """Compute eval_quality as win rate (draws = 0.5).

    Args:
        matches: List of {"winner": "candidate"|"champion"|"draw"}

    Returns:
        Score 0.0-1.0
    """
    if not matches:
        return 0.0
    score = sum(
        1.0 if m["winner"] == "candidate" else 0.5 if m["winner"] == "draw" else 0.0
        for m in matches
    )
    return score / len(matches)


def compute_trigger_accuracy(cases: list[dict]) -> float:
    """Compute trigger accuracy as proportion of correct predictions.

    Args:
        cases: List of {"expected_trigger": bool, "actual_trigger": bool}

    Returns:
        Score 0.0-1.0
    """
    if not cases:
        return 0.0
    correct = sum(1 for c in cases if c["expected_trigger"] == c["actual_trigger"])
    return correct / len(cases)


def compute_token_efficiency(
    champion_avg_tokens: int, candidate_avg_tokens: int
) -> float:
    """Compute token efficiency as normalized ratio.

    Neutral point is 0.5 (no change). >0.5 = candidate more concise.

    Args:
        champion_avg_tokens: Average token count of champion outputs
        candidate_avg_tokens: Average token count of candidate outputs

    Returns:
        Score 0.0-1.0
    """
    if candidate_avg_tokens == 0:
        return 0.5  # can't compute ratio, return neutral
    ratio = champion_avg_tokens / candidate_avg_tokens
    return min(ratio, 2.0) / 2.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_metrics.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/metrics.py tests/test_metrics.py
git commit -m "feat: metric computation for eval_quality, trigger_accuracy, token_efficiency"
```

---

## Task 4: Promotion Decision Tree (`scripts/promotion.py`)

**Files:**
- Create: `scripts/promotion.py`
- Create: `tests/test_promotion.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_promotion.py
import json
from scripts.promotion import decide_promotion


class TestDecidePromotion:
    def _config(self, **overrides):
        config = {
            "metrics": {
                "eval_quality": {"tolerance": 0.02, "minimum": 0.6},
                "trigger_accuracy": {"tolerance": 0.05, "minimum": 0.7},
                "token_efficiency": {"tolerance": 0.10, "minimum": None},
            },
            "elo_confidence_threshold": 1520,
            "elo_minimum_matches": 5,
        }
        config.update(overrides)
        return config

    def test_all_checks_pass_returns_keep(self):
        result = decide_promotion(
            config=self._config(),
            candidate_elo=1530,
            matches_played=6,
            metrics_old={"eval_quality": 0.72, "trigger_accuracy": 0.85, "token_efficiency": 0.50},
            metrics_new={"eval_quality": 0.78, "trigger_accuracy": 0.84, "token_efficiency": 0.52},
        )
        assert result["decision"] == "keep"

    def test_below_minimum_matches_returns_defer(self):
        result = decide_promotion(
            config=self._config(),
            candidate_elo=1530,
            matches_played=3,
            metrics_old={"eval_quality": 0.72},
            metrics_new={"eval_quality": 0.80},
        )
        assert result["decision"] == "defer"

    def test_metric_below_hard_floor_returns_discard(self):
        result = decide_promotion(
            config=self._config(),
            candidate_elo=1530,
            matches_played=6,
            metrics_old={"eval_quality": 0.65, "trigger_accuracy": 0.80},
            metrics_new={"eval_quality": 0.55, "trigger_accuracy": 0.80},  # below 0.6 floor
        )
        assert result["decision"] == "discard"
        assert "hard floor" in result["reason"].lower()

    def test_elo_below_threshold_returns_discard(self):
        result = decide_promotion(
            config=self._config(),
            candidate_elo=1505,
            matches_played=6,
            metrics_old={"eval_quality": 0.72},
            metrics_new={"eval_quality": 0.75},
        )
        assert result["decision"] == "discard"
        assert "elo" in result["reason"].lower()

    def test_regression_beyond_tolerance_returns_discard(self):
        result = decide_promotion(
            config=self._config(),
            candidate_elo=1530,
            matches_played=6,
            metrics_old={"eval_quality": 0.80, "trigger_accuracy": 0.90},
            metrics_new={"eval_quality": 0.85, "trigger_accuracy": 0.80},  # -0.10 > tolerance 0.05
        )
        assert result["decision"] == "discard"
        assert "tolerance" in result["reason"].lower()

    def test_no_improvement_returns_discard(self):
        result = decide_promotion(
            config=self._config(),
            candidate_elo=1530,
            matches_played=6,
            metrics_old={"eval_quality": 0.80, "trigger_accuracy": 0.90},
            metrics_new={"eval_quality": 0.80, "trigger_accuracy": 0.90},  # identical
        )
        assert result["decision"] == "discard"

    def test_null_minimum_skips_floor_check(self):
        result = decide_promotion(
            config=self._config(),
            candidate_elo=1530,
            matches_played=6,
            metrics_old={"token_efficiency": 0.50},
            metrics_new={"token_efficiency": 0.55},  # no floor for token_efficiency
        )
        assert result["decision"] == "keep"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_promotion.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `scripts/promotion.py`**

```python
# scripts/promotion.py
"""Promotion decision tree: should a candidate skill version be kept or discarded?"""


def decide_promotion(
    config: dict,
    candidate_elo: float,
    matches_played: int,
    metrics_old: dict[str, float],
    metrics_new: dict[str, float],
) -> dict:
    """Apply the promotion decision tree.

    Returns:
        {"decision": "keep"|"discard"|"defer", "reason": "..."}
    """
    # Step 1: Minimum matches gate
    min_matches = config.get("elo_minimum_matches", 5)
    if matches_played < min_matches:
        return {"decision": "defer", "reason": f"Only {matches_played}/{min_matches} matches played"}

    # Step 2: Hard floor check
    metric_configs = config.get("metrics", {})
    for metric_name, new_value in metrics_new.items():
        mc = metric_configs.get(metric_name, {})
        minimum = mc.get("minimum")
        if minimum is not None and new_value < minimum:
            return {
                "decision": "discard",
                "reason": f"Hard floor violation: {metric_name}={new_value:.3f} < minimum={minimum}",
            }

    # Step 3: ELO confidence check
    elo_threshold = config.get("elo_confidence_threshold", 1520)
    if candidate_elo < elo_threshold:
        return {
            "decision": "discard",
            "reason": f"ELO {candidate_elo:.0f} < threshold {elo_threshold}",
        }

    # Step 4: Pareto tolerance check
    any_improved = False
    for metric_name in metrics_new:
        old_val = metrics_old.get(metric_name, 0.0)
        new_val = metrics_new[metric_name]
        delta = new_val - old_val

        if delta > 0:
            any_improved = True
        elif delta < 0:
            mc = metric_configs.get(metric_name, {})
            tolerance = mc.get("tolerance", 0.0)
            if abs(delta) > tolerance:
                return {
                    "decision": "discard",
                    "reason": f"Tolerance exceeded: {metric_name} regressed by {abs(delta):.3f} > tolerance={tolerance}",
                }

    if not any_improved:
        return {"decision": "discard", "reason": "No metric improved"}

    return {"decision": "keep", "reason": "All checks passed"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_promotion.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/promotion.py tests/test_promotion.py
git commit -m "feat: promotion decision tree with floor, ELO, and Pareto checks"
```

---

## Task 5: Experiment Log Management (`scripts/experiment_log.py`)

**Files:**
- Create: `scripts/experiment_log.py`
- Create: `tests/test_experiment_log.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_experiment_log.py
import json
from pathlib import Path
from scripts.experiment_log import (
    create_empty_log,
    add_entry,
    prune_log,
    read_log,
)


class TestCreateEmptyLog:
    def test_creates_valid_structure(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        data = json.loads(log_path.read_text())
        assert data["entries"] == []
        assert "lessons_summary" not in data


class TestAddEntry:
    def test_adds_entry(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        entry = {
            "iteration": 1,
            "commit": "abc1234",
            "hypothesis": "test",
            "change_summary": "test change",
            "metrics": {},
            "elo": {},
            "outcome": "kept",
            "lessons": "it worked",
        }
        add_entry(log_path, entry)
        data = read_log(log_path)
        assert len(data["entries"]) == 1
        assert "timestamp" in data["entries"][0]


class TestPruneLog:
    def test_prunes_discarded_entries_fifo(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        # Add 55 discarded entries
        for i in range(55):
            add_entry(log_path, {
                "iteration": i,
                "commit": f"d{i:04d}",
                "hypothesis": f"hyp {i}",
                "change_summary": f"change {i}",
                "metrics": {},
                "elo": {},
                "outcome": "discarded",
                "lessons": "",
            })
        prune_log(log_path, max_discarded=50)
        data = read_log(log_path)
        discarded = [e for e in data["entries"] if e["outcome"] == "discarded"]
        assert len(discarded) == 50
        # Oldest should be removed (iterations 0-4 gone)
        iterations = [e["iteration"] for e in discarded]
        assert min(iterations) == 5

    def test_keeps_kept_entries_during_prune(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        # Add 10 kept + 55 discarded
        for i in range(10):
            add_entry(log_path, {
                "iteration": i, "commit": f"k{i:04d}",
                "hypothesis": "", "change_summary": "", "metrics": {},
                "elo": {}, "outcome": "kept", "lessons": f"lesson {i}",
            })
        for i in range(10, 65):
            add_entry(log_path, {
                "iteration": i, "commit": f"d{i:04d}",
                "hypothesis": "", "change_summary": "", "metrics": {},
                "elo": {}, "outcome": "discarded", "lessons": "",
            })
        prune_log(log_path, max_discarded=50)
        data = read_log(log_path)
        kept = [e for e in data["entries"] if e["outcome"] == "kept"]
        assert len(kept) == 10  # all kept entries preserved

    def test_summarizes_old_kept_entries(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        # Add 35 kept entries
        for i in range(35):
            add_entry(log_path, {
                "iteration": i, "commit": f"k{i:04d}",
                "hypothesis": f"hyp {i}", "change_summary": f"change {i}",
                "metrics": {}, "elo": {}, "outcome": "kept",
                "lessons": f"lesson {i}",
            })
        prune_log(log_path, max_discarded=50, max_kept_detailed=30)
        data = read_log(log_path)
        kept = [e for e in data["entries"] if e["outcome"] == "kept"]
        assert len(kept) == 30
        assert "lessons_summary" in data
        assert len(data["lessons_summary"]) == 5  # 35 - 30 = 5 summarized
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_experiment_log.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `scripts/experiment_log.py`**

```python
# scripts/experiment_log.py
"""Experiment log management with pruning and cap enforcement."""

import json
from datetime import datetime, timezone
from pathlib import Path


def create_empty_log(log_path: Path) -> None:
    """Create an empty experiment log."""
    log_path.write_text(json.dumps({"entries": []}, indent=2))


def read_log(log_path: Path) -> dict:
    """Read the experiment log."""
    return json.loads(log_path.read_text())


def add_entry(log_path: Path, entry: dict) -> None:
    """Add an entry to the experiment log."""
    data = read_log(log_path)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    data["entries"].append(entry)
    log_path.write_text(json.dumps(data, indent=2))


def prune_log(
    log_path: Path,
    max_discarded: int = 50,
    max_kept_detailed: int = 30,
) -> None:
    """Prune the log to enforce caps.

    - Discarded entries: FIFO, capped at max_discarded
    - Kept entries: if > max_kept_detailed, oldest are summarized
    """
    data = read_log(log_path)
    entries = data["entries"]

    kept = [e for e in entries if e["outcome"] == "kept"]
    discarded = [e for e in entries if e["outcome"] != "kept"]

    # Prune discarded (FIFO)
    if len(discarded) > max_discarded:
        discarded = discarded[-max_discarded:]

    # Summarize old kept entries
    if len(kept) > max_kept_detailed:
        to_summarize = kept[: len(kept) - max_kept_detailed]
        kept = kept[len(kept) - max_kept_detailed :]

        summaries = data.get("lessons_summary", [])
        for entry in to_summarize:
            summaries.append(
                f"iter {entry['iteration']}: {entry.get('lessons', entry.get('change_summary', ''))}"
            )
        data["lessons_summary"] = summaries

    data["entries"] = kept + discarded
    log_path.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_experiment_log.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/experiment_log.py tests/test_experiment_log.py
git commit -m "feat: experiment log with CRUD, FIFO pruning, and kept entry summarization"
```

---

## Task 6: Changelog Generator (`scripts/changelog.py`)

**Files:**
- Create: `scripts/changelog.py`
- Create: `tests/test_changelog.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_changelog.py
from scripts.changelog import generate_changelog


class TestGenerateChangelog:
    def test_empty_log(self):
        result = generate_changelog("my-skill", {"entries": []})
        assert "# Changelog" in result
        assert "my-skill" in result

    def test_kept_entries_appear(self):
        log = {"entries": [
            {
                "iteration": 1,
                "timestamp": "2026-03-20T22:15:00Z",
                "commit": "abc1234",
                "change_summary": "Added step numbering",
                "metrics": {"eval_quality": {"old": 0.72, "new": 0.78, "delta": 0.06}},
                "outcome": "kept",
            },
        ]}
        result = generate_changelog("my-skill", log, version="1.0.1")
        assert "v1.0.1" in result
        assert "Added step numbering" in result
        assert "0.72" in result
        assert "0.78" in result

    def test_discarded_entries_excluded(self):
        log = {"entries": [
            {"iteration": 1, "outcome": "discarded", "change_summary": "Bad change"},
            {"iteration": 2, "outcome": "kept", "change_summary": "Good change",
             "timestamp": "2026-03-20T22:15:00Z", "commit": "abc1234",
             "metrics": {"eval_quality": {"old": 0.70, "new": 0.75, "delta": 0.05}}},
        ]}
        result = generate_changelog("my-skill", log)
        assert "Bad change" not in result
        assert "Good change" in result

    def test_multiple_kept_entries_ordered_newest_first(self):
        log = {"entries": [
            {"iteration": 1, "outcome": "kept", "change_summary": "First",
             "timestamp": "2026-03-20T20:00:00Z", "commit": "aaa",
             "metrics": {"eval_quality": {"old": 0.70, "new": 0.75, "delta": 0.05}}},
            {"iteration": 2, "outcome": "kept", "change_summary": "Second",
             "timestamp": "2026-03-20T21:00:00Z", "commit": "bbb",
             "metrics": {"eval_quality": {"old": 0.75, "new": 0.80, "delta": 0.05}}},
        ]}
        result = generate_changelog("my-skill", log)
        second_pos = result.index("Second")
        first_pos = result.index("First")
        assert second_pos < first_pos  # newest first
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_changelog.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `scripts/changelog.py`**

```python
# scripts/changelog.py
"""Generate changelog from experiment log kept entries."""


def generate_changelog(
    skill_name: str, log: dict, version: str | None = None
) -> str:
    """Generate a markdown changelog from kept experiment log entries.

    Args:
        skill_name: Name of the skill
        log: The experiment log dict with "entries" key
        version: Optional version string for the latest entry

    Returns:
        Markdown-formatted changelog string
    """
    kept = [e for e in log.get("entries", []) if e.get("outcome") == "kept"]
    kept.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    lines = [f"# Changelog — {skill_name}", ""]

    for i, entry in enumerate(kept):
        v = version if i == 0 and version else f"v?.?.{len(kept) - i}"
        date = entry.get("timestamp", "unknown")[:10]
        summary = entry.get("change_summary", "No description")

        lines.append(f"## {v} ({date})")

        metric_parts = []
        for metric_name, values in entry.get("metrics", {}).items():
            if isinstance(values, dict) and "old" in values and "new" in values:
                metric_parts.append(
                    f"{metric_name}: {values['old']:.2f} → {values['new']:.2f}"
                )
        metric_str = f" ({', '.join(metric_parts)})" if metric_parts else ""

        lines.append(f"- Improved: {summary}{metric_str}")
        lines.append("")

    if not kept:
        lines.append("No improvements yet.")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_changelog.py -v`
Expected: All PASS

- [ ] **Step 5: Create `scripts/version.py`**

```python
# scripts/version.py
"""Bump patch version in plugin.json."""

import json
from pathlib import Path


def bump_patch(plugin_json_path: Path) -> str:
    """Bump the patch version and return the new version string."""
    data = json.loads(plugin_json_path.read_text())
    version = data.get("version", "1.0.0")
    parts = version.split(".")
    parts[2] = str(int(parts[2]) + 1)
    new_version = ".".join(parts)
    data["version"] = new_version
    plugin_json_path.write_text(json.dumps(data, indent=2))
    return new_version


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bump patch version")
    parser.add_argument("--plugin-json", required=True, help="Path to plugin.json")
    args = parser.parse_args()

    new_version = bump_patch(Path(args.plugin_json))
    print(json.dumps({"version": new_version}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Commit**

```bash
git add scripts/changelog.py scripts/version.py tests/test_changelog.py
git commit -m "feat: changelog generator and version bumper"
```

---

## Task 7: Lockfile Concurrency Guard (`scripts/lockfile.py`)

**Files:**
- Create: `scripts/lockfile.py`
- Create: `tests/test_lockfile.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lockfile.py
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.lockfile import acquire_lock, release_lock, refresh_lock, is_locked


class TestAcquireLock:
    def test_creates_lock_file(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        result = acquire_lock(lock_path, skill="test-skill")
        assert result is True
        assert lock_path.exists()
        data = json.loads(lock_path.read_text())
        assert data["skill"] == "test-skill"
        assert "pid" in data
        assert "started_at" in data

    def test_refuses_if_lock_exists_and_fresh(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="first")
        result = acquire_lock(lock_path, skill="second")
        assert result is False

    def test_overwrites_stale_lock(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        lock_path.write_text(json.dumps({
            "pid": 99999, "started_at": stale_time, "skill": "old"
        }))
        result = acquire_lock(lock_path, skill="new", stale_hours=4)
        assert result is True
        data = json.loads(lock_path.read_text())
        assert data["skill"] == "new"


class TestReleaseLock:
    def test_deletes_lock_file(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="test")
        release_lock(lock_path)
        assert not lock_path.exists()

    def test_noop_if_no_lock(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        release_lock(lock_path)  # should not raise


class TestRefreshLock:
    def test_updates_timestamp(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="test")
        old_data = json.loads(lock_path.read_text())
        refresh_lock(lock_path)
        new_data = json.loads(lock_path.read_text())
        assert new_data["started_at"] >= old_data["started_at"]


class TestIsLocked:
    def test_returns_false_when_no_lock(self, tmp_path):
        assert is_locked(tmp_path / ".autoresearch.lock") is False

    def test_returns_true_when_locked(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="test")
        assert is_locked(lock_path) is True

    def test_returns_false_when_stale(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        lock_path.write_text(json.dumps({
            "pid": 99999, "started_at": stale_time, "skill": "old"
        }))
        assert is_locked(lock_path, stale_hours=4) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_lockfile.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `scripts/lockfile.py`**

```python
# scripts/lockfile.py
"""Concurrency guard for the autoresearch loop."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


def acquire_lock(
    lock_path: Path, skill: str, stale_hours: int = 4
) -> bool:
    """Attempt to acquire the autoresearch lock.

    Returns True if lock acquired, False if another instance is running.
    """
    if lock_path.exists():
        if not _is_stale(lock_path, stale_hours):
            return False

    lock_data = {
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
    }
    lock_path.write_text(json.dumps(lock_data, indent=2))
    return True


def release_lock(lock_path: Path) -> None:
    """Release the autoresearch lock."""
    if lock_path.exists():
        lock_path.unlink()


def refresh_lock(lock_path: Path) -> None:
    """Refresh the lock timestamp to prevent staleness."""
    if lock_path.exists():
        data = json.loads(lock_path.read_text())
        data["started_at"] = datetime.now(timezone.utc).isoformat()
        lock_path.write_text(json.dumps(data, indent=2))


def is_locked(lock_path: Path, stale_hours: int = 4) -> bool:
    """Check if the autoresearch lock is held and not stale."""
    if not lock_path.exists():
        return False
    return not _is_stale(lock_path, stale_hours)


def _is_stale(lock_path: Path, stale_hours: int) -> bool:
    """Check if a lock file is stale."""
    data = json.loads(lock_path.read_text())
    started = datetime.fromisoformat(data["started_at"])
    return datetime.now(timezone.utc) - started > timedelta(hours=stale_hours)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_lockfile.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lockfile.py tests/test_lockfile.py
git commit -m "feat: lockfile concurrency guard with staleness detection"
```

---

## Task 8: Example Plugin (Greeter)

**Files:**
- Create: `plugins/example-greeter/.claude-plugin/plugin.json`
- Create: `plugins/example-greeter/skills/example-greeter/SKILL.md`
- Create: `plugins/example-greeter/evals/cases.json`
- Create: `plugins/example-greeter/evals/config.json`
- Create: `plugins/example-greeter/experiments/log.json`
- Create: `plugins/example-greeter/experiments/elo.json`
- Create: `plugins/example-greeter/experiments/changelog.md`
- Modify: `.claude-plugin/marketplace.json` (add the plugin entry)

- [ ] **Step 1: Create plugin metadata**

`plugins/example-greeter/.claude-plugin/plugin.json`:
```json
{
  "name": "example-greeter",
  "description": "A friendly greeting skill that welcomes users and offers help",
  "version": "1.0.0"
}
```

- [ ] **Step 2: Create the skill**

`plugins/example-greeter/skills/example-greeter/SKILL.md`:
```markdown
---
name: example-greeter
description: "Use when the user greets you or says hello, hi, hey, or similar greeting. Responds with a friendly, personalized greeting and offers to help."
---

# Greeting Handler

When the user greets you:

1. Respond with a warm, friendly greeting
2. Acknowledge the time of day if known
3. Briefly mention you're ready to help with their project
4. Ask what they'd like to work on

Keep the greeting concise (2-3 sentences). Do not be overly enthusiastic or use excessive punctuation.
```

- [ ] **Step 3: Create eval cases (6 cases, meeting the ≥5 threshold)**

`plugins/example-greeter/evals/cases.json`:
```json
[
  {
    "id": "simple-hello",
    "input": "Hello!",
    "expected_trigger": true,
    "rubric": "Should respond with a friendly greeting and offer to help. Should NOT be overly enthusiastic or use excessive exclamation marks. Should ask what the user wants to work on."
  },
  {
    "id": "casual-hey",
    "input": "hey",
    "expected_trigger": true,
    "rubric": "Should handle casual greeting naturally. Should not be stiff or overly formal. Should offer help."
  },
  {
    "id": "good-morning",
    "input": "Good morning!",
    "expected_trigger": true,
    "rubric": "Should acknowledge the time of day (morning). Should respond warmly and offer to help."
  },
  {
    "id": "negative-code-question",
    "input": "How do I fix this TypeScript error?",
    "expected_trigger": false,
    "rubric": "This is a technical question, not a greeting. The greeting skill should NOT trigger."
  },
  {
    "id": "negative-file-request",
    "input": "Read the file src/index.ts",
    "expected_trigger": false,
    "rubric": "This is a file operation request, not a greeting. The greeting skill should NOT trigger."
  },
  {
    "id": "greeting-with-context",
    "input": "Hi there, I'm working on a React app",
    "expected_trigger": true,
    "rubric": "Should greet the user AND acknowledge that they're working on a React app. Should offer to help with the React project specifically."
  }
]
```

- [ ] **Step 4: Create eval config and experiment files**

`plugins/example-greeter/evals/config.json`:
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

`plugins/example-greeter/experiments/log.json`:
```json
{
  "entries": []
}
```

`plugins/example-greeter/experiments/elo.json` — will be initialized by the orchestrator on first run.

`plugins/example-greeter/experiments/changelog.md`:
```markdown
# Changelog — example-greeter

No improvements yet.
```

- [ ] **Step 5: Update marketplace.json to include the plugin**

Add to `.claude-plugin/marketplace.json` `plugins` array:
```json
{
  "name": "example-greeter",
  "description": "A friendly greeting skill that welcomes users and offers help",
  "source": "./plugins/example-greeter",
  "category": "productivity"
}
```

- [ ] **Step 6: Commit**

```bash
git add plugins/example-greeter/ .claude-plugin/marketplace.json
git commit -m "feat: add example-greeter plugin with 6 eval cases"
```

---

## Task 9: Skill Executor Agent

**Files:**
- Create: `.claude/agents/skill-executor.md`

- [ ] **Step 1: Create the skill executor agent definition**

`.claude/agents/skill-executor.md`:
```markdown
---
name: skill-executor
description: Executes a skill against an eval case and returns the output, token count, and trigger status
tools: Bash, Read, Write
model: sonnet
---

<purpose>
You execute a Claude Code skill against a single eval case and report the results.
You receive skill content and an eval input, set up a temporary project directory with the skill loaded, run it via the claude CLI, and return structured results.
</purpose>

<instructions>
You will receive a task with these fields:
- skill_content: The full SKILL.md text to test
- skill_name: The name of the skill
- eval_input: The user prompt to test against
- eval_context: Optional context description

Follow these steps exactly:

1. Create a temporary project directory that mimics a Claude Code project:
   ```bash
   TMPDIR=$(mktemp -d /tmp/autoresearch-eval-XXXXXX)
   mkdir -p "$TMPDIR/.claude/skills/{skill_name}"
   ```

2. Write the skill_content to the SKILL.md file:
   ```bash
   cat > "$TMPDIR/.claude/skills/{skill_name}/SKILL.md" << 'SKILLEOF'
   {skill_content}
   SKILLEOF
   ```

3. Remove the CLAUDECODE env var (allows nesting claude -p inside a Claude Code session) and run the eval:
   ```bash
   env -u CLAUDECODE claude -p "{eval_input}" --output-format stream-json --cwd "$TMPDIR" 2>/dev/null
   ```
   The `--cwd` flag tells Claude CLI to use the temp directory as the project root, which causes it to discover and load the skill from `$TMPDIR/.claude/skills/`.

4. Parse the stream-json output to determine:
   - Whether the skill was triggered (look for `"type": "tool_use"` with `"name": "Skill"` and the skill name in the input, OR `"name": "Read"` with the skill path)
   - The full text output from the assistant (concatenate all `content_block_delta` text deltas)
   - Approximate token count (from the `"usage"` field in the `message_stop` event, or count words × 1.3 as fallback)

5. Clean up the temporary directory:
   ```bash
   rm -rf "$TMPDIR"
   ```

6. Return a JSON object to stdout:
   {"output": "full response text", "token_count": 1234, "triggered": true}

If the claude command fails or times out (120s), return:
   {"output": "", "token_count": 0, "triggered": false, "error": "description"}
</instructions>
```

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/skill-executor.md
git commit -m "feat: skill-executor agent definition"
```

---

## Task 10: Skill Judge Agent

**Files:**
- Create: `.claude/agents/skill-judge.md`

- [ ] **Step 1: Create the skill judge agent definition**

`.claude/agents/skill-judge.md`:
```markdown
---
name: skill-judge
description: Compares two anonymized skill outputs head-to-head against a rubric and picks a winner
tools: []
model: sonnet
---

<purpose>
You are an impartial judge comparing two AI assistant responses. You receive two responses (labeled "Response A" and "Response B") and a rubric describing what a good response looks like. You must pick a winner or declare a draw.
</purpose>

<instructions>
You will receive:
- response_a: The text of Response A
- response_b: The text of Response B
- rubric: A plain-English description of what a good response looks like

Evaluate both responses against the rubric. Consider:
1. Does the response follow the rubric's requirements?
2. Is the response accurate and helpful?
3. Is the response well-structured and clear?
4. Does the response avoid the rubric's stated anti-patterns?

You MUST NOT consider:
- Response length (unless the rubric specifically mentions it)
- Formatting preferences (unless the rubric specifically mentions it)
- Your own opinions about what a good response looks like — only the rubric matters

After evaluation, respond with ONLY a JSON object:
{"winner": "A", "reasoning": "Response A better addressed the rubric requirement to..."}

Or:
{"winner": "B", "reasoning": "Response B better addressed..."}

Or:
{"winner": "draw", "reasoning": "Both responses equally addressed..."}

Do not include any text before or after the JSON object.
</instructions>
```

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/skill-judge.md
git commit -m "feat: skill-judge agent definition for head-to-head comparison"
```

---

## Task 11: Orchestrator Skill (`/autoresearch`)

**Files:**
- Create: `.claude/skills/autoresearch/SKILL.md`

- [ ] **Step 1: Create the orchestrator skill**

`.claude/skills/autoresearch/SKILL.md`:
```markdown
---
name: autoresearch
description: "Use when the user wants to run the autonomous skill optimization loop. Iteratively improves skills in the marketplace by modifying SKILL.md files, evaluating changes via head-to-head ELO ranking, and keeping improvements."
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Agent, Glob, Grep
---

# AutoSkillResearch Orchestrator

You are the autonomous skill optimization loop. You modify skills, evaluate them, and keep improvements.

## Invocation

- `/autoresearch` — optimize all skills in round-robin rotation
- `/autoresearch <skill-name>` — optimize a single skill

## Startup

1. Check the concurrency lock:
   ```bash
   python3 scripts/lockfile.py check --lock-path .autoresearch.lock
   ```
   If locked, print the lock info and stop.

2. Acquire the lock:
   ```bash
   python3 scripts/lockfile.py acquire --lock-path .autoresearch.lock --skill "<first-skill>"
   ```

3. Read `program.md` for the global optimization strategy.

4. List all optimized-tier skills:
   - Glob for `plugins/*/evals/cases.json`
   - For each, verify it has ≥5 eval cases
   - If `$ARGUMENTS` specifies a skill name, filter to just that skill

5. For the current skill, create or switch to the working branch:
   ```bash
   git checkout -B autoresearch/<skill-name>
   ```
   This creates the branch if it doesn't exist, or switches to it if it does.

## The Loop

For each skill in rotation, run `iterations_per_rotation` iterations (read from `evals/config.json`, default 10):

### Per-Iteration Steps

**1. Read Context**
Read these files for the current skill:
- `plugins/<skill>/evals/config.json`
- `plugins/<skill>/evals/cases.json`
- `plugins/<skill>/experiments/log.json`
- `plugins/<skill>/skills/<skill>/SKILL.md`
- `plugins/<skill>/optimize.md` (if exists)
- `program.md`

**2. Hypothesize**
Based on the experiment log (what worked, what failed) and the optimization strategy:
- Form a clear hypothesis about what change will improve the skill
- Write the hypothesis down before making any changes
- Make ONE focused change per iteration
- Save the current SKILL.md content as `champion_content` (you need it for comparison)

**3. Modify**
- Edit the SKILL.md file to implement your hypothesis
- Commit the change:
  ```bash
  git add plugins/<skill>/skills/<skill>/SKILL.md
  git commit -m "autoresearch: <one-line hypothesis>"
  ```

**4. Evaluate**
For each eval case in `cases.json`:

a. **Run candidate skill** — dispatch a `skill-executor` agent with:
   - The modified SKILL.md content
   - The eval case input and context

b. **Run champion skill** — dispatch a `skill-executor` agent with:
   - The saved `champion_content`
   - The same eval case input and context

c. **Judge** — dispatch a `skill-judge` agent with:
   - Both outputs (randomized order, anonymized as A/B)
   - The eval case rubric

d. **Record results** — for each case, record:
   - Winner (candidate/champion/draw)
   - Trigger status (did the skill trigger?)
   - Token counts

If a subagent fails, log it and continue with remaining cases.
If ≥50% of cases error, abort this iteration.

**5. Compute Metrics**
Write match results and trigger results to temp files to avoid shell escaping issues:
```bash
echo '<matches_json>' > /tmp/ar-matches.json
echo '<triggers_json>' > /tmp/ar-triggers.json
python3 scripts/metrics.py --matches-file /tmp/ar-matches.json --triggers-file /tmp/ar-triggers.json --champion-tokens <n> --candidate-tokens <n>
```

**6. Update ELO**
For each match result:
```bash
python3 scripts/elo.py update --elo-path plugins/<skill>/experiments/elo.json --candidate-commit <hash> --result <A|B|draw>
```

**7. Decide: Keep or Discard**
Write metrics to temp files:
```bash
echo '<metrics_old_json>' > /tmp/ar-metrics-old.json
echo '<metrics_new_json>' > /tmp/ar-metrics-new.json
python3 scripts/promotion.py --config plugins/<skill>/evals/config.json --elo <candidate_elo> --matches <n> --metrics-old-file /tmp/ar-metrics-old.json --metrics-new-file /tmp/ar-metrics-new.json
```

If **keep**:
- Update experiment log:
  ```bash
  python3 scripts/experiment_log.py add --log-path plugins/<skill>/experiments/log.json --entry '<json>'
  python3 scripts/experiment_log.py prune --log-path plugins/<skill>/experiments/log.json
  ```
- Update ELO state to promote:
  ```bash
  python3 scripts/elo.py update --elo-path plugins/<skill>/experiments/elo.json --candidate-commit <hash> --result promote
  ```
- Generate changelog:
  ```bash
  python3 scripts/changelog.py --skill-name <name> --log-path plugins/<skill>/experiments/log.json --output plugins/<skill>/experiments/changelog.md
  ```
- Bump version:
  ```bash
  python3 scripts/version.py --plugin-json plugins/<skill>/.claude-plugin/plugin.json
  ```
- Commit all state files:
  ```bash
  git add plugins/<skill>/experiments/ plugins/<skill>/.claude-plugin/plugin.json
  git commit -m "autoresearch: keep — <hypothesis summary>"
  ```

If **discard**:
- Revert the SKILL.md change:
  ```bash
  git reset --hard HEAD~1
  ```
- Log the discarded attempt:
  ```bash
  python3 scripts/experiment_log.py add --log-path plugins/<skill>/experiments/log.json --entry '<json>'
  ```
- Commit the log update:
  ```bash
  git add plugins/<skill>/experiments/log.json
  git commit -m "autoresearch: discard — <hypothesis summary>"
  ```

**8. Check Exit Conditions**
- If `iterations_per_rotation` reached → move to next skill
- If all metrics at ceiling (eval_quality ≥ 0.95, trigger_accuracy ≥ 0.95) → move to next skill early
- Otherwise → loop back to Step 1

**9. Refresh Lock**
Every 30 minutes (track wall clock time):
```bash
python3 scripts/lockfile.py refresh
```

## Shutdown

On completion or interruption:
```bash
python3 scripts/lockfile.py release
```

## Error Recovery

If you encounter an error:
1. Log it in the experiment log with outcome "error"
2. Revert any uncommitted changes: `git checkout -- .`
3. Continue to the next iteration
4. If 3 consecutive errors on the same skill, move to the next skill

## Key Rules

- Do NOT pause to ask the human if you should continue
- Do NOT make multiple changes per iteration
- Do NOT skip the hypothesis step — always write it down before editing
- Do NOT modify any file other than the skill's SKILL.md during the modify step
- Always save champion_content BEFORE modifying the SKILL.md
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/autoresearch/SKILL.md
git commit -m "feat: autoresearch orchestrator skill"
```

---

## Task 12: Add CLI Interfaces to Python Scripts

**Files:**
- Modify: `scripts/elo.py` (add CLI main)
- Modify: `scripts/metrics.py` (add CLI main)
- Modify: `scripts/promotion.py` (add CLI main)
- Modify: `scripts/experiment_log.py` (add CLI main)
- Modify: `scripts/changelog.py` (add CLI main)
- Modify: `scripts/lockfile.py` (add CLI main)

The orchestrator skill calls these scripts via `python3 scripts/<name>.py <args>`. Each script needs an `argparse` CLI that reads JSON from args or stdin and prints JSON to stdout.

- [ ] **Step 1: Add CLI to `scripts/elo.py`**

Add at bottom of `scripts/elo.py`:
```python
def main():
    import argparse

    parser = argparse.ArgumentParser(description="ELO rating operations")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create initial ELO state")
    init.add_argument("--elo-path", required=True)
    init.add_argument("--champion-commit", required=True)

    update = sub.add_parser("update", help="Update ELO after match/decision")
    update.add_argument("--elo-path", required=True)
    update.add_argument("--candidate-commit", required=True)
    update.add_argument("--result", required=True, choices=["A", "B", "draw", "promote", "discard"])

    args = parser.parse_args()

    if args.command == "init":
        state = create_initial_elo_state(args.champion_commit)
        Path(args.elo_path).write_text(json.dumps(state, indent=2))
        print(json.dumps(state, indent=2))
    elif args.command == "update":
        state = update_elo_state(Path(args.elo_path), args.candidate_commit, args.result)
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add CLI to `scripts/metrics.py`**

Add at bottom of `scripts/metrics.py`:
```python
def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Compute metrics from raw eval data")
    parser.add_argument("--matches-file", help="Path to JSON file of match results")
    parser.add_argument("--triggers-file", help="Path to JSON file of trigger results")
    parser.add_argument("--champion-tokens", type=int, default=0)
    parser.add_argument("--candidate-tokens", type=int, default=0)
    args = parser.parse_args()

    result = {}
    if args.matches_file:
        matches = json.loads(Path(args.matches_file).read_text())
        result["eval_quality"] = compute_eval_quality(matches)
    if args.triggers_file:
        triggers = json.loads(Path(args.triggers_file).read_text())
        result["trigger_accuracy"] = compute_trigger_accuracy(triggers)
    if args.champion_tokens and args.candidate_tokens:
        result["token_efficiency"] = compute_token_efficiency(
            args.champion_tokens, args.candidate_tokens
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Add CLI to `scripts/promotion.py`**

Add at bottom of `scripts/promotion.py`:
```python
def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Promotion decision tree")
    parser.add_argument("--config", required=True, help="Path to eval config JSON")
    parser.add_argument("--elo", type=float, required=True)
    parser.add_argument("--matches", type=int, required=True)
    parser.add_argument("--metrics-old-file", required=True, help="Path to JSON file of old metrics")
    parser.add_argument("--metrics-new-file", required=True, help="Path to JSON file of new metrics")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text())
    result = decide_promotion(
        config=config,
        candidate_elo=args.elo,
        matches_played=args.matches,
        metrics_old=json.loads(Path(args.metrics_old_file).read_text()),
        metrics_new=json.loads(Path(args.metrics_new_file).read_text()),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add CLI to `scripts/experiment_log.py`**

Add at bottom of `scripts/experiment_log.py`:
```python
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Experiment log management")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create empty log")
    init_cmd.add_argument("--log-path", required=True)

    add_cmd = sub.add_parser("add", help="Add entry to log")
    add_cmd.add_argument("--log-path", required=True)
    add_cmd.add_argument("--entry", required=True, help="JSON entry")

    prune_cmd = sub.add_parser("prune", help="Prune log to enforce caps")
    prune_cmd.add_argument("--log-path", required=True)
    prune_cmd.add_argument("--max-discarded", type=int, default=50)
    prune_cmd.add_argument("--max-kept-detailed", type=int, default=30)

    read_cmd = sub.add_parser("read", help="Read and print log")
    read_cmd.add_argument("--log-path", required=True)

    args = parser.parse_args()

    if args.command == "init":
        create_empty_log(Path(args.log_path))
        print('{"status": "created"}')
    elif args.command == "add":
        entry = json.loads(args.entry)
        add_entry(Path(args.log_path), entry)
        print('{"status": "added"}')
    elif args.command == "prune":
        prune_log(Path(args.log_path), args.max_discarded, args.max_kept_detailed)
        print('{"status": "pruned"}')
    elif args.command == "read":
        data = read_log(Path(args.log_path))
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add CLI to `scripts/changelog.py`**

Add at bottom of `scripts/changelog.py`:
```python
def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Generate changelog")
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--version", default=None)
    args = parser.parse_args()

    log = json.loads(Path(args.log_path).read_text())
    changelog = generate_changelog(args.skill_name, log, version=args.version)
    Path(args.output).write_text(changelog)
    print(f'{{"status": "written", "path": "{args.output}"}}')


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Add CLI to `scripts/lockfile.py`**

Add at bottom of `scripts/lockfile.py`:
```python
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Autoresearch lockfile management")
    sub = parser.add_subparsers(dest="command", required=True)

    acquire_cmd = sub.add_parser("acquire", help="Acquire lock")
    acquire_cmd.add_argument("--skill", required=True)
    acquire_cmd.add_argument("--lock-path", default=".autoresearch.lock")
    acquire_cmd.add_argument("--stale-hours", type=int, default=4)

    release_cmd = sub.add_parser("release", help="Release lock")
    release_cmd.add_argument("--lock-path", default=".autoresearch.lock")

    refresh_cmd = sub.add_parser("refresh", help="Refresh lock timestamp")
    refresh_cmd.add_argument("--lock-path", default=".autoresearch.lock")

    check_cmd = sub.add_parser("check", help="Check if locked")
    check_cmd.add_argument("--lock-path", default=".autoresearch.lock")
    check_cmd.add_argument("--stale-hours", type=int, default=4)

    args = parser.parse_args()

    if args.command == "acquire":
        result = acquire_lock(Path(args.lock_path), args.skill, args.stale_hours)
        status = "acquired" if result else "blocked"
        print(json.dumps({"status": status}))
    elif args.command == "release":
        release_lock(Path(args.lock_path))
        print('{"status": "released"}')
    elif args.command == "refresh":
        refresh_lock(Path(args.lock_path))
        print('{"status": "refreshed"}')
    elif args.command == "check":
        locked = is_locked(Path(args.lock_path), args.stale_hours)
        info = {}
        if locked:
            info = json.loads(Path(args.lock_path).read_text())
        print(json.dumps({"locked": locked, **info}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Run all tests to verify nothing broke**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add scripts/
git commit -m "feat: add CLI interfaces to all Python scripts"
```

---

## Task 13: Integration Test — Full Loop Dry Run

**Files:**
- Create: `tests/test_integration.py`

This test exercises the full pipeline with the example-greeter plugin using the Python scripts only (no Claude API calls). It validates that all scripts work together correctly.

- [ ] **Step 1: Write the integration test**

```python
# tests/test_integration.py
"""Integration test: exercises all Python scripts in sequence, simulating one loop iteration."""

import json
from pathlib import Path
from scripts.elo import create_initial_elo_state, update_elo_state
from scripts.metrics import compute_eval_quality, compute_trigger_accuracy, compute_token_efficiency
from scripts.promotion import decide_promotion
from scripts.experiment_log import create_empty_log, add_entry, prune_log, read_log
from scripts.changelog import generate_changelog
from scripts.lockfile import acquire_lock, release_lock, is_locked


def test_full_loop_simulation(tmp_path):
    """Simulate one complete iteration of the autoresearch loop using scripts."""
    skill_dir = tmp_path / "plugins" / "test-skill"
    skill_dir.mkdir(parents=True)
    experiments_dir = skill_dir / "experiments"
    experiments_dir.mkdir()
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir()

    # 1. Setup: create initial state files
    lock_path = tmp_path / ".autoresearch.lock"
    elo_path = experiments_dir / "elo.json"
    log_path = experiments_dir / "log.json"

    assert acquire_lock(lock_path, skill="test-skill")
    assert is_locked(lock_path)

    elo_state = create_initial_elo_state("initial01")
    elo_path.write_text(json.dumps(elo_state, indent=2))
    create_empty_log(log_path)

    config = {
        "metrics": {
            "eval_quality": {"tolerance": 0.02, "minimum": 0.6},
            "trigger_accuracy": {"tolerance": 0.05, "minimum": 0.7},
        },
        "elo_confidence_threshold": 1520,
        "elo_minimum_matches": 5,
    }
    (evals_dir / "config.json").write_text(json.dumps(config))

    # 2. Simulate eval results (as if subagents ran)
    match_results = [
        {"winner": "candidate"},  # case 1: candidate wins
        {"winner": "candidate"},  # case 2: candidate wins
        {"winner": "candidate"},  # case 3: candidate wins
        {"winner": "draw"},       # case 4: draw
        {"winner": "champion"},   # case 5: champion wins
        {"winner": "candidate"},  # case 6: candidate wins
    ]
    trigger_results = [
        {"expected_trigger": True, "actual_trigger": True},
        {"expected_trigger": True, "actual_trigger": True},
        {"expected_trigger": True, "actual_trigger": True},
        {"expected_trigger": False, "actual_trigger": False},
        {"expected_trigger": False, "actual_trigger": False},
        {"expected_trigger": True, "actual_trigger": True},
    ]

    # 3. Compute metrics
    eval_quality = compute_eval_quality(match_results)
    trigger_accuracy = compute_trigger_accuracy(trigger_results)
    token_efficiency = compute_token_efficiency(150, 120)  # champion 150, candidate 120

    assert eval_quality > 0.6  # 4.5/6 = 0.75
    assert trigger_accuracy == 1.0
    assert token_efficiency > 0.5  # candidate is more concise

    # 4. Update ELO for each match
    candidate_commit = "cand0001"
    for match in match_results:
        winner = "A" if match["winner"] == "candidate" else "B" if match["winner"] == "champion" else "draw"
        update_elo_state(elo_path, candidate_commit, winner)

    elo_state = json.loads(elo_path.read_text())
    assert elo_state["candidate"]["matches_played"] == 6
    candidate_elo = elo_state["candidate"]["elo"]

    # 5. Promotion decision
    metrics_old = {"eval_quality": 0.50, "trigger_accuracy": 0.85}
    metrics_new = {"eval_quality": eval_quality, "trigger_accuracy": trigger_accuracy}
    decision = decide_promotion(
        config=config,
        candidate_elo=candidate_elo,
        matches_played=6,
        metrics_old=metrics_old,
        metrics_new=metrics_new,
    )
    assert decision["decision"] == "keep"

    # 6. Log the result
    add_entry(log_path, {
        "iteration": 1,
        "commit": candidate_commit,
        "hypothesis": "Test hypothesis",
        "change_summary": "Test change",
        "metrics": {
            "eval_quality": {"old": 0.50, "new": eval_quality, "delta": eval_quality - 0.50},
            "trigger_accuracy": {"old": 0.85, "new": trigger_accuracy, "delta": trigger_accuracy - 0.85},
        },
        "elo": {
            "starting": 1500,
            "final": candidate_elo,
            "matches": 6,
            "wins": 4,
            "losses": 1,
            "draws": 1,
        },
        "outcome": "kept",
        "lessons": "Test lesson",
    })
    log_data = read_log(log_path)
    assert len(log_data["entries"]) == 1

    # 7. Generate changelog
    changelog = generate_changelog("test-skill", log_data, version="v1.0.1")
    assert "v1.0.1" in changelog
    assert "Test change" in changelog

    # 8. Promote in ELO
    update_elo_state(elo_path, candidate_commit, "promote")
    final_elo = json.loads(elo_path.read_text())
    assert final_elo["current_champion"]["commit"] == candidate_commit
    assert final_elo["candidate"] is None

    # 9. Release lock
    release_lock(lock_path)
    assert not is_locked(lock_path)
```

- [ ] **Step 2: Run the integration test**

Run: `python3 -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration test simulating full autoresearch loop iteration"
```

---

## Task 14: Add `.gitignore` and Final Cleanup

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.autoresearch.lock
/tmp/
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **Step 2: Run the full test suite one final time**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

## Summary

| Task | Component | Files | Tests |
|------|-----------|-------|-------|
| 1 | Scaffolding & marketplace | 10 created | — |
| 2 | ELO system | 2 created | 8 tests |
| 3 | Metrics computation | 2 created | 12 tests |
| 4 | Promotion decision tree | 2 created | 7 tests |
| 5 | Experiment log | 2 created | 6 tests |
| 6 | Changelog generator | 2 created | 3 tests |
| 7 | Lockfile guard | 2 created | 7 tests |
| 8 | Example plugin | 7 created, 1 modified | — |
| 9 | Skill executor agent | 1 created | — |
| 10 | Skill judge agent | 1 created | — |
| 11 | Orchestrator skill | 1 created | — |
| 12 | CLI interfaces | 6 modified | — |
| 13 | Integration test | 1 created | 1 test |
| 14 | Cleanup | 1 created | — |

**Total:** 14 tasks, ~40 files, ~44 tests

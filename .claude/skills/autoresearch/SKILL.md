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
   - For each, verify it has >=5 eval cases
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
- Write the champion content to a temp file for cache lookups:
  ```bash
  cp plugins/<skill>/skills/<skill>/SKILL.md /tmp/ar-champion.md
  ```

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

b. **Run champion skill (with caching)** — first check the cache:
   ```bash
   python3 scripts/champion_cache.py get --cache-dir plugins/<skill>/experiments/.cache --champion-content-file /tmp/ar-champion.md --case-id <case_id>
   ```
   - If the result contains `"hit": true`, use the cached `output`, `token_count`, and `triggered` values. Do NOT dispatch a skill-executor agent.
   - If the result contains `"hit": false`, dispatch a `skill-executor` agent with the saved `champion_content` and the eval case input/context. Then cache the result:
     ```bash
     python3 scripts/champion_cache.py put --cache-dir plugins/<skill>/experiments/.cache --champion-content-file /tmp/ar-champion.md --case-id <case_id> --result '<executor_result_json>'
     ```

c. **Judge** — dispatch a `skill-judge` agent with:
   - Both outputs (randomized order, anonymized as A/B)
   - The eval case rubric

d. **Record results** — for each case, record:
   - Winner (candidate/champion/draw)
   - Trigger status (did the skill trigger?)
   - Token counts

If a subagent fails, log it and continue with remaining cases.
If >=50% of cases error, abort this iteration and revert.

**5. Compute Metrics**
Write match and trigger results to temp files, then compute:
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
- Invalidate the champion cache (the champion is about to change):
  ```bash
  python3 scripts/champion_cache.py invalidate --cache-dir plugins/<skill>/experiments/.cache
  ```
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
- Finalize ELO state for the discarded candidate:
  ```bash
  python3 scripts/elo.py update --elo-path plugins/<skill>/experiments/elo.json --candidate-commit <hash> --result discard
  ```
- Log the discarded attempt:
  ```bash
  python3 scripts/experiment_log.py add --log-path plugins/<skill>/experiments/log.json --entry '<json>'
  ```
- Commit the log update:
  ```bash
  git add plugins/<skill>/experiments/log.json plugins/<skill>/experiments/elo.json
  git commit -m "autoresearch: discard — <hypothesis summary>"
  ```

**8. Check Exit Conditions**
- If `iterations_per_rotation` reached -> move to next skill
- If all metrics at ceiling (eval_quality >= 0.95, trigger_accuracy >= 0.95) -> move to next skill early
- Otherwise -> loop back to Step 1

**9. Refresh Lock**
Every 30 minutes (track wall clock time):
```bash
python3 scripts/lockfile.py refresh --lock-path .autoresearch.lock
```

## Shutdown

On completion or interruption:
```bash
python3 scripts/lockfile.py release --lock-path .autoresearch.lock
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

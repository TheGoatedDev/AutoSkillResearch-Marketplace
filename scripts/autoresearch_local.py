"""Standalone local autoresearch orchestrator.

Drives the skill optimization loop using a local LLM for hypothesis/judging
and cloud Claude Code for skill execution.
"""

import argparse
import json
import random
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.champion_cache import ChampionCache, ExecutionResult
from scripts.cloud_executor import CloudExecutor
from scripts.config_loader import Config, load_config
from scripts.llm_client import LocalLLMClient
from scripts.retry import with_retry

# Import existing scripts as modules
from scripts import elo as elo_mod
from scripts import metrics as metrics_mod
from scripts import promotion as promotion_mod
from scripts import experiment_log as log_mod
from scripts import changelog as changelog_mod
from scripts import version as version_mod
from scripts import lockfile as lockfile_mod

console = Console()


@dataclass
class SkillContext:
    name: str
    plugin_dir: Path
    skill_md_path: Path
    cases: list[dict]
    config: dict
    elo_path: Path
    log_path: Path
    plugin_json_path: Path
    changelog_path: Path
    cache_dir: Path


@dataclass
class IterationOutcome:
    hypothesis: str
    decision: str  # "keep", "discard", "error"
    reason: str
    metrics: dict = field(default_factory=dict)
    elo: float = 0.0
    error: str | None = None


def discover_skills(project_root: Path, skill_filter: str | None = None) -> list[SkillContext]:
    """Find all skills with >=5 eval cases."""
    skills: list[SkillContext] = []
    plugins_dir = project_root / "plugins"
    if not plugins_dir.exists():
        return skills

    for cases_path in sorted(plugins_dir.glob("*/evals/cases.json")):
        skill_name = cases_path.parent.parent.name
        if skill_filter and skill_name != skill_filter:
            continue

        cases = json.loads(cases_path.read_text())
        if len(cases) < 5:
            continue

        plugin_dir = cases_path.parent.parent
        config_path = plugin_dir / "evals" / "config.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}

        skills.append(SkillContext(
            name=skill_name,
            plugin_dir=plugin_dir,
            skill_md_path=plugin_dir / "skills" / skill_name / "SKILL.md",
            cases=cases,
            config=config,
            elo_path=plugin_dir / "experiments" / "elo.json",
            log_path=plugin_dir / "experiments" / "log.json",
            plugin_json_path=plugin_dir / ".claude-plugin" / "plugin.json",
            changelog_path=plugin_dir / "experiments" / "changelog.md",
            cache_dir=plugin_dir / "experiments" / ".cache",
        ))

    return skills


def run_iteration(
    ctx: SkillContext,
    llm: LocalLLMClient,
    executor: CloudExecutor,
    program_strategy: str,
    iteration_num: int,
    dry_run: bool = False,
) -> IterationOutcome:
    """Run one iteration of the optimization loop for a skill."""
    champion_content = ctx.skill_md_path.read_text()
    experiment_log = log_mod.read_log(ctx.log_path)

    # Load optional optimize.md hints
    optimize_path = ctx.plugin_dir / "optimize.md"
    optimize_hints = optimize_path.read_text() if optimize_path.exists() else None

    # 1. Generate hypothesis via local LLM
    console.print("  [dim]Generating hypothesis...[/dim]")
    hyp_result = with_retry(
        lambda: llm.generate_hypothesis(
            skill_content=champion_content,
            experiment_log=experiment_log,
            program_strategy=program_strategy,
            eval_cases=ctx.cases,
            optimize_hints=optimize_hints,
        ),
        max_retries=3,
        base_delay=1.0,
        retry_on=(Exception,),
    )
    console.print(f"  Hypothesis: [cyan]{hyp_result.hypothesis}[/cyan]")

    if dry_run:
        return IterationOutcome(hypothesis=hyp_result.hypothesis, decision="dry-run", reason="Dry run mode")

    # 2. Write candidate SKILL.md and commit
    project_root = ctx.plugin_dir.parent.parent
    ctx.skill_md_path.write_text(hyp_result.new_skill_content)
    subprocess.run(
        ["git", "add", str(ctx.skill_md_path)],
        cwd=project_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"autoresearch: {hyp_result.hypothesis[:72]}"],
        cwd=project_root, check=True, capture_output=True,
    )
    candidate_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root, check=True, capture_output=True, text=True,
    ).stdout.strip()

    candidate_content = hyp_result.new_skill_content
    cache = ChampionCache(ctx.cache_dir)

    # 3. Evaluate each case
    matches: list[dict] = []
    trigger_results: list[dict] = []
    champion_tokens_total = 0
    candidate_tokens_total = 0
    errors = 0

    table = Table(title=f"Eval Cases \u2014 Iteration {iteration_num}")
    table.add_column("Case")
    table.add_column("Winner")
    table.add_column("Triggered")

    for case in ctx.cases:
        case_id = case["id"]
        console.print(f"  [dim]Evaluating case: {case_id}[/dim]")

        try:
            # Champion (from cache or cloud)
            champion_result = cache.get(champion_content, case_id)
            if champion_result is None:
                champion_result = with_retry(
                    lambda _ci=case_id, _cc=champion_content: executor.execute(
                        skill_content=_cc,
                        skill_name=ctx.name,
                        eval_input=case["input"],
                        eval_context=case.get("context", {}).get("description") if isinstance(case.get("context"), dict) else None,
                    ),
                    max_retries=3, base_delay=1.0,
                )
                if champion_result.error is None:
                    cache.put(champion_content, case_id, champion_result)

            # Candidate (always cloud)
            candidate_result = with_retry(
                lambda _case=case: executor.execute(
                    skill_content=candidate_content,
                    skill_name=ctx.name,
                    eval_input=_case["input"],
                    eval_context=_case.get("context", {}).get("description") if isinstance(_case.get("context"), dict) else None,
                ),
                max_retries=3, base_delay=1.0,
            )

            if champion_result.error or candidate_result.error:
                errors += 1
                table.add_row(case_id, "[red]ERROR[/red]", "-")
                continue

            # Judge -- randomize A/B assignment
            if random.random() < 0.5:
                resp_a, resp_b = candidate_result.output, champion_result.output
                candidate_is_a = True
            else:
                resp_a, resp_b = champion_result.output, candidate_result.output
                candidate_is_a = False

            judge_result = with_retry(
                lambda _ra=resp_a, _rb=resp_b, _rubric=case["rubric"]: llm.judge(
                    response_a=_ra,
                    response_b=_rb,
                    rubric=_rubric,
                ),
                max_retries=3, base_delay=1.0,
            )

            # Map winner back
            if judge_result.winner == "draw":
                match_winner = "draw"
            elif judge_result.winner == "A":
                match_winner = "candidate" if candidate_is_a else "champion"
            else:
                match_winner = "champion" if candidate_is_a else "candidate"

            matches.append({"winner": match_winner, "case_id": case_id})

            # Trigger results
            trigger_results.append({
                "expected_trigger": case["expected_trigger"],
                "actual_trigger": candidate_result.triggered,
            })

            champion_tokens_total += champion_result.token_count
            candidate_tokens_total += candidate_result.token_count

            winner_display = {"candidate": "[green]candidate[/green]", "champion": "[red]champion[/red]", "draw": "[yellow]draw[/yellow]"}
            table.add_row(case_id, winner_display.get(match_winner, match_winner), str(candidate_result.triggered))

            # Update ELO per match — candidate is always position A
            elo_result = "A" if match_winner == "candidate" else ("B" if match_winner == "champion" else "draw")
            elo_mod.update_elo_state(ctx.elo_path, candidate_commit, elo_result)

        except Exception as e:
            errors += 1
            table.add_row(case_id, f"[red]ERROR: {str(e)[:30]}[/red]", "-")

    console.print(table)

    if errors > len(ctx.cases) * 0.5:
        _revert_candidate(ctx)
        return IterationOutcome(hypothesis=hyp_result.hypothesis, decision="error", reason=f"{errors}/{len(ctx.cases)} cases errored")

    # 4. Compute metrics
    champion_avg_tokens = champion_tokens_total // max(len(matches), 1)
    candidate_avg_tokens = candidate_tokens_total // max(len(matches), 1)

    new_metrics = {
        "eval_quality": metrics_mod.compute_eval_quality(matches),
        "trigger_accuracy": metrics_mod.compute_trigger_accuracy(trigger_results),
        "token_efficiency": metrics_mod.compute_token_efficiency(champion_avg_tokens, candidate_avg_tokens),
    }

    # Get old metrics from last kept entry, or defaults
    old_metrics = _get_old_metrics(experiment_log)

    # 5. Read ELO state for decision
    elo_state = json.loads(ctx.elo_path.read_text())
    candidate_elo = elo_state.get("candidate", {}).get("elo", 1500) if elo_state.get("candidate") else 1500
    matches_played = elo_state.get("candidate", {}).get("matches_played", 0) if elo_state.get("candidate") else 0

    # 6. Decide
    decision = promotion_mod.decide_promotion(
        config=ctx.config,
        candidate_elo=candidate_elo,
        matches_played=matches_played,
        metrics_old=old_metrics,
        metrics_new=new_metrics,
    )

    outcome = IterationOutcome(
        hypothesis=hyp_result.hypothesis,
        decision=decision["decision"],
        reason=decision["reason"],
        metrics=new_metrics,
        elo=candidate_elo,
    )

    # 7. Apply decision
    if decision["decision"] in ("keep", "kept"):
        _apply_keep(ctx, hyp_result.hypothesis, new_metrics, old_metrics, candidate_elo, candidate_commit, iteration_num)
        cache.invalidate()
    elif decision["decision"] == "discard":
        _apply_discard(ctx, hyp_result.hypothesis, new_metrics, candidate_elo, candidate_commit, iteration_num)
    elif decision["decision"] == "defer":
        _apply_discard(ctx, hyp_result.hypothesis, new_metrics, candidate_elo, candidate_commit, iteration_num)
        outcome.decision = "discard"
        outcome.reason = decision["reason"]

    return outcome


def _get_old_metrics(experiment_log: dict) -> dict:
    """Get metrics from the last kept entry, or defaults."""
    for entry in reversed(experiment_log.get("entries", [])):
        if entry.get("outcome") in ("keep", "kept"):
            m = entry.get("metrics", {})
            if m:
                return {k: v.get("new", v) if isinstance(v, dict) else v for k, v in m.items()}
    return {"eval_quality": 0.5, "trigger_accuracy": 0.5, "token_efficiency": 0.5}


def _revert_candidate(ctx: SkillContext) -> None:
    """Revert the candidate commit."""
    subprocess.run(
        ["git", "reset", "--hard", "HEAD~1"],
        cwd=ctx.plugin_dir.parent.parent, check=True, capture_output=True,
    )


def _apply_keep(
    ctx: SkillContext,
    hypothesis: str,
    new_metrics: dict,
    old_metrics: dict,
    candidate_elo: float,
    candidate_commit: str,
    iteration_num: int,
) -> None:
    project_root = ctx.plugin_dir.parent.parent

    log_entry = {
        "iteration": iteration_num,
        "hypothesis": hypothesis,
        "outcome": "keep",
        "metrics": {k: {"old": old_metrics.get(k, 0), "new": v} for k, v in new_metrics.items()},
        "elo": candidate_elo,
        "reason": "All checks passed",
    }
    log_mod.add_entry(ctx.log_path, log_entry)
    log_mod.prune_log(ctx.log_path)

    elo_mod.update_elo_state(ctx.elo_path, candidate_commit, "promote")

    log_data = log_mod.read_log(ctx.log_path)
    new_version = version_mod.bump_patch(ctx.plugin_json_path)
    changelog_text = changelog_mod.generate_changelog(ctx.name, log_data, version=new_version)
    ctx.changelog_path.write_text(changelog_text)

    subprocess.run(
        ["git", "add",
         str(ctx.elo_path), str(ctx.log_path), str(ctx.changelog_path),
         str(ctx.plugin_json_path)],
        cwd=project_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"autoresearch: keep \u2014 {hypothesis[:60]}"],
        cwd=project_root, check=True, capture_output=True,
    )


def _apply_discard(
    ctx: SkillContext,
    hypothesis: str,
    new_metrics: dict,
    candidate_elo: float,
    candidate_commit: str,
    iteration_num: int,
) -> None:
    project_root = ctx.plugin_dir.parent.parent

    _revert_candidate(ctx)

    elo_mod.update_elo_state(ctx.elo_path, candidate_commit, "discard")

    log_entry = {
        "iteration": iteration_num,
        "hypothesis": hypothesis,
        "outcome": "discard",
        "metrics": new_metrics,
        "elo": candidate_elo,
        "reason": "Discarded",
    }
    log_mod.add_entry(ctx.log_path, log_entry)

    subprocess.run(
        ["git", "add", str(ctx.log_path), str(ctx.elo_path)],
        cwd=project_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"autoresearch: discard \u2014 {hypothesis[:60]}"],
        cwd=project_root, check=True, capture_output=True,
    )


def run_loop(config: Config, project_root: Path) -> None:
    """Main entry point: discover skills and run the optimization loop."""
    lock_path = project_root / ".autoresearch.lock"

    console.print(Panel(
        f"[bold]Local AutoResearch[/bold]\n"
        f"Model: {config.local_llm_model} @ {config.local_llm_base_url}\n"
        f"Iterations: {config.iterations_per_rotation}\n"
        f"Skill filter: {config.skill or 'all eligible'}",
        title="Config",
    ))

    skills = discover_skills(project_root, skill_filter=config.skill)
    if not skills:
        console.print("[red]No eligible skills found (need >=5 eval cases).[/red]")
        return

    console.print(f"Found {len(skills)} eligible skill(s): {', '.join(s.name for s in skills)}")

    program_path = project_root / "program.md"
    program_strategy = program_path.read_text() if program_path.exists() else ""

    llm = LocalLLMClient(
        base_url=config.local_llm_base_url,
        model=config.local_llm_model,
        timeout=config.local_llm_timeout,
    )
    executor = CloudExecutor(
        claude_command=config.claude_command,
        timeout=config.execution_timeout,
    )

    first_skill = skills[0].name
    if not lockfile_mod.acquire_lock(lock_path, first_skill):
        lock_data = lockfile_mod.read_lock(lock_path)
        console.print(f"[red]Lock held by PID {lock_data.get('pid')} for skill {lock_data.get('skill')}. Exiting.[/red]")
        return

    try:
        for skill_ctx in skills:
            _run_skill_rotation(config, skill_ctx, llm, executor, program_strategy, project_root, lock_path)
    finally:
        lockfile_mod.release_lock(lock_path)
        console.print("[dim]Lock released.[/dim]")


def _run_skill_rotation(
    config: Config,
    ctx: SkillContext,
    llm: LocalLLMClient,
    executor: CloudExecutor,
    program_strategy: str,
    project_root: Path,
    lock_path: Path,
) -> None:
    console.print(f"\n[bold blue]{'='*60}[/bold blue]")
    console.print(f"[bold blue]Optimizing: {ctx.name}[/bold blue]")
    console.print(f"[bold blue]{'='*60}[/bold blue]\n")

    subprocess.run(
        ["git", "checkout", "-B", f"autoresearch/{ctx.name}"],
        cwd=project_root, check=True, capture_output=True,
    )

    consecutive_errors = 0
    outcomes: list[IterationOutcome] = []
    iterations = config.iterations_per_rotation

    for i in range(1, iterations + 1):
        console.print(f"\n[bold]--- Iteration {i}/{iterations} ---[/bold]")

        try:
            outcome = run_iteration(
                ctx=ctx,
                llm=llm,
                executor=executor,
                program_strategy=program_strategy,
                iteration_num=i,
                dry_run=config.dry_run,
            )
            outcomes.append(outcome)

            if outcome.decision == "error":
                consecutive_errors += 1
                console.print(f"  [red]ERROR: {outcome.reason}[/red]")
            else:
                consecutive_errors = 0
                color = "green" if outcome.decision == "keep" else "red"
                console.print(f"  [{color}]{outcome.decision.upper()}[/{color}]: {outcome.reason}")
                if outcome.metrics:
                    for k, v in outcome.metrics.items():
                        console.print(f"    {k}: {v:.3f}")
                console.print(f"    ELO: {outcome.elo:.1f}")

        except Exception as e:
            consecutive_errors += 1
            outcomes.append(IterationOutcome(hypothesis="", decision="error", reason=str(e), error=str(e)))
            console.print(f"  [red]FATAL ERROR: {e}[/red]")

        if consecutive_errors >= config.max_consecutive_errors:
            console.print(f"\n[red]{consecutive_errors} consecutive errors. Stopping.[/red]")
            break

        # Check ceiling
        if outcome.metrics:
            eq = outcome.metrics.get("eval_quality", 0)
            ta = outcome.metrics.get("trigger_accuracy", 0)
            if eq >= 0.95 and ta >= 0.95:
                console.print(f"\n[green]Ceiling reached (eval_quality={eq:.2f}, trigger_accuracy={ta:.2f}). Moving on.[/green]")
                break

        # Refresh lock periodically
        if i % 5 == 0:
            lockfile_mod.refresh_lock(lock_path)

    _print_summary(ctx.name, outcomes)


def _print_summary(skill_name: str, outcomes: list[IterationOutcome]) -> None:
    table = Table(title=f"Summary \u2014 {skill_name}")
    table.add_column("#", style="dim")
    table.add_column("Hypothesis")
    table.add_column("Decision")
    table.add_column("ELO")

    for i, o in enumerate(outcomes, 1):
        color = {"keep": "green", "discard": "red", "error": "red", "dry-run": "dim"}.get(o.decision, "white")
        table.add_row(str(i), o.hypothesis[:50], f"[{color}]{o.decision}[/{color}]", f"{o.elo:.0f}" if o.elo else "-")

    console.print(table)

    keeps = sum(1 for o in outcomes if o.decision == "keep")
    discards = sum(1 for o in outcomes if o.decision == "discard")
    errors_count = sum(1 for o in outcomes if o.decision == "error")
    console.print(f"\n[bold]Results:[/bold] {keeps} kept, {discards} discarded, {errors_count} errors")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local autoresearch orchestrator")
    parser.add_argument("--skill", help="Optimize a single skill (default: all eligible)")
    parser.add_argument("--model", help="Override local LLM model name")
    parser.add_argument("--base-url", help="Override local LLM endpoint URL")
    parser.add_argument("--iterations", type=int, help="Override iterations per rotation")
    parser.add_argument("--config", default="autoresearch_local.yaml", help="Path to config YAML")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    args = parser.parse_args()

    project_root = Path.cwd()
    config = load_config(
        config_path=Path(args.config),
        cli_model=args.model,
        cli_base_url=args.base_url,
        cli_iterations=args.iterations,
        cli_skill=args.skill,
        cli_dry_run=args.dry_run,
    )

    run_loop(config, project_root)


if __name__ == "__main__":
    main()

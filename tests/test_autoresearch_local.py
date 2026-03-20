import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.autoresearch_local import discover_skills, run_iteration, IterationOutcome, SkillContext
from scripts.champion_cache import ExecutionResult
from scripts.elo import create_initial_elo_state
from scripts.llm_client import HypothesisResult, JudgeResult


class TestDiscoverSkills:
    def _setup_skill(self, plugins_dir: Path, name: str, num_cases: int) -> None:
        skill_dir = plugins_dir / name
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir(parents=True)
        cases = [{"id": f"c{i}", "input": f"test {i}", "expected_trigger": True, "rubric": "rubric"} for i in range(num_cases)]
        (evals_dir / "cases.json").write_text(json.dumps(cases))
        (evals_dir / "config.json").write_text(json.dumps({"metrics": {}, "iterations_per_rotation": 10}))
        skill_content_dir = skill_dir / "skills" / name
        skill_content_dir.mkdir(parents=True)
        (skill_content_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\nContent")
        experiments_dir = skill_dir / "experiments"
        experiments_dir.mkdir(parents=True)
        (experiments_dir / "log.json").write_text(json.dumps({"entries": []}))
        (experiments_dir / "elo.json").write_text(json.dumps(create_initial_elo_state("abc")))
        plugin_dir = skill_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({"name": name, "version": "1.0.0"}))

    def test_finds_skills_with_enough_cases(self, tmp_path):
        self._setup_skill(tmp_path / "plugins", "good-skill", 6)
        self._setup_skill(tmp_path / "plugins", "too-few", 3)
        skills = discover_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "good-skill"

    def test_filters_by_skill_name(self, tmp_path):
        self._setup_skill(tmp_path / "plugins", "skill-a", 6)
        self._setup_skill(tmp_path / "plugins", "skill-b", 6)
        skills = discover_skills(tmp_path, skill_filter="skill-a")
        assert len(skills) == 1
        assert skills[0].name == "skill-a"

    def test_returns_empty_when_no_eligible(self, tmp_path):
        (tmp_path / "plugins").mkdir()
        skills = discover_skills(tmp_path)
        assert skills == []


class TestRunIteration:
    """Integration-style test for a single iteration with all components mocked."""

    @pytest.fixture(autouse=True)
    def git_repo(self, tmp_path):
        """Initialize a git repo in tmp_path so git commands work."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    def _make_skill_context(self, tmp_path) -> SkillContext:
        plugins_dir = tmp_path / "plugins" / "test-skill"
        evals_dir = plugins_dir / "evals"
        evals_dir.mkdir(parents=True)
        cases = [
            {"id": "c1", "input": "hello", "expected_trigger": True, "rubric": "greet warmly"},
            {"id": "c2", "input": "fix bug", "expected_trigger": False, "rubric": "should not trigger"},
        ]
        (evals_dir / "cases.json").write_text(json.dumps(cases))
        config = {
            "metrics": {
                "eval_quality": {"tolerance": 0.02, "minimum": 0.6},
                "trigger_accuracy": {"tolerance": 0.05, "minimum": 0.7},
                "token_efficiency": {"tolerance": 0.10, "minimum": None},
            },
            "elo_confidence_threshold": 1520,
            "elo_minimum_matches": 5,
        }
        (evals_dir / "config.json").write_text(json.dumps(config))
        skill_content_dir = plugins_dir / "skills" / "test-skill"
        skill_content_dir.mkdir(parents=True)
        (skill_content_dir / "SKILL.md").write_text("---\nname: test-skill\n---\nOriginal")
        experiments_dir = plugins_dir / "experiments"
        experiments_dir.mkdir(parents=True)
        (experiments_dir / "log.json").write_text(json.dumps({"entries": []}))
        elo_state = create_initial_elo_state("abc123")
        (experiments_dir / "elo.json").write_text(json.dumps(elo_state))
        plugin_dir = plugins_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "test-skill", "version": "1.0.0"}))

        # Stage all files so git knows about them
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add skill"], cwd=tmp_path, check=True, capture_output=True)

        return SkillContext(
            name="test-skill",
            plugin_dir=plugins_dir,
            skill_md_path=skill_content_dir / "SKILL.md",
            cases=cases,
            config=config,
            elo_path=experiments_dir / "elo.json",
            log_path=experiments_dir / "log.json",
            plugin_json_path=plugin_dir / "plugin.json",
            changelog_path=experiments_dir / "changelog.md",
            cache_dir=experiments_dir / ".cache",
        )

    def test_iteration_returns_outcome(self, tmp_path):
        ctx = self._make_skill_context(tmp_path)
        mock_llm = MagicMock()
        mock_llm.generate_hypothesis.return_value = HypothesisResult(
            hypothesis="test change",
            new_skill_content="---\nname: test-skill\n---\nModified",
        )
        mock_llm.judge.return_value = JudgeResult(winner="A", reasoning="candidate better")

        mock_executor = MagicMock()
        mock_executor.execute.return_value = ExecutionResult(
            output="response text", token_count=100, triggered=True, error=None,
        )

        outcome = run_iteration(
            ctx=ctx,
            llm=mock_llm,
            executor=mock_executor,
            program_strategy="strategy",
            iteration_num=1,
            dry_run=False,
        )
        assert isinstance(outcome, IterationOutcome)
        assert outcome.hypothesis == "test change"
        assert mock_llm.generate_hypothesis.call_count == 1
        assert mock_llm.judge.call_count == 2
        assert mock_executor.execute.call_count >= 2

    def test_dry_run_skips_execution(self, tmp_path):
        ctx = self._make_skill_context(tmp_path)
        mock_llm = MagicMock()
        mock_llm.generate_hypothesis.return_value = HypothesisResult(
            hypothesis="dry run test",
            new_skill_content="new content",
        )
        mock_executor = MagicMock()

        outcome = run_iteration(
            ctx=ctx,
            llm=mock_llm,
            executor=mock_executor,
            program_strategy="strategy",
            iteration_num=1,
            dry_run=True,
        )
        assert outcome.decision == "dry-run"
        assert mock_executor.execute.call_count == 0

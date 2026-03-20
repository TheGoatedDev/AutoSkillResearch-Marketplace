import json
import subprocess
from unittest.mock import patch, MagicMock
from scripts.cloud_executor import CloudExecutor
from scripts.champion_cache import ExecutionResult


class TestCloudExecutor:
    def _make_executor(self) -> CloudExecutor:
        return CloudExecutor(claude_command="claude", timeout=30)

    def _stream_json_output(self, text: str, triggered: bool, tokens: int = 100) -> str:
        """Build a realistic stream-json output string."""
        lines = []
        lines.append(json.dumps({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}))
        if triggered:
            lines.append(json.dumps({"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "test-skill"}}}))
            lines.append(json.dumps({"type": "content_block_stop", "index": 1}))
        lines.append(json.dumps({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}}))
        lines.append(json.dumps({"type": "content_block_stop", "index": 0}))
        lines.append(json.dumps({"type": "message_stop", "usage": {"input_tokens": 50, "output_tokens": tokens}}))
        return "\n".join(lines)

    @patch("scripts.cloud_executor.subprocess.run")
    def test_successful_execution(self, mock_run):
        output = self._stream_json_output("Hello there!", triggered=True, tokens=150)
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        executor = self._make_executor()
        result = executor.execute(
            skill_content="---\nname: test-skill\n---\nContent",
            skill_name="test-skill",
            eval_input="Hello!",
        )
        assert isinstance(result, ExecutionResult)
        assert result.output == "Hello there!"
        assert result.triggered is True
        assert result.token_count == 150
        assert result.error is None

    @patch("scripts.cloud_executor.subprocess.run")
    def test_no_trigger_detected(self, mock_run):
        output = self._stream_json_output("Generic response", triggered=False, tokens=80)
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        executor = self._make_executor()
        result = executor.execute(
            skill_content="---\nname: test-skill\n---\nContent",
            skill_name="test-skill",
            eval_input="Fix the bug",
        )
        assert result.triggered is False

    @patch("scripts.cloud_executor.subprocess.run")
    def test_timeout_returns_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        executor = self._make_executor()
        result = executor.execute(
            skill_content="content",
            skill_name="test-skill",
            eval_input="hello",
        )
        assert result.error is not None
        assert result.output == ""
        assert result.token_count == 0

    @patch("scripts.cloud_executor.subprocess.run")
    def test_nonzero_exit_returns_error(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=1, stderr="crash")
        executor = self._make_executor()
        result = executor.execute(
            skill_content="content",
            skill_name="test-skill",
            eval_input="hello",
        )
        assert result.error is not None

    @patch("scripts.cloud_executor.subprocess.run")
    def test_eval_context_prepended_to_input(self, mock_run):
        output = self._stream_json_output("response", triggered=False)
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        executor = self._make_executor()
        executor.execute(
            skill_content="content",
            skill_name="test-skill",
            eval_input="Do the thing",
            eval_context="A Python web project with Flask",
        )
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args", [])
        # The -p argument should contain the context
        p_idx = cmd.index("-p")
        prompt_arg = cmd[p_idx + 1]
        assert "Python web project" in prompt_arg

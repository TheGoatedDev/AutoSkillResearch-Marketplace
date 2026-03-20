"""Cloud executor: runs skills via claude -p CLI for high-fidelity evaluation."""

import json
import subprocess
import tempfile
from pathlib import Path

from scripts.champion_cache import ExecutionResult


class CloudExecutor:
    def __init__(self, claude_command: str = "claude", timeout: int = 120) -> None:
        self._claude_command = claude_command
        self._timeout = timeout

    def execute(
        self,
        skill_content: str,
        skill_name: str,
        eval_input: str,
        eval_context: str | None = None,
    ) -> ExecutionResult:
        tmpdir = tempfile.mkdtemp(prefix="autoresearch-eval-")
        try:
            return self._run(tmpdir, skill_content, skill_name, eval_input, eval_context)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _run(
        self,
        tmpdir: str,
        skill_content: str,
        skill_name: str,
        eval_input: str,
        eval_context: str | None,
    ) -> ExecutionResult:
        # Set up skill directory
        skill_dir = Path(tmpdir) / ".claude" / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Build prompt
        prompt = eval_input
        if eval_context:
            prompt = f"Given a project with {eval_context}: {eval_input}"

        # Run claude -p
        cmd = [
            "env", "-u", "CLAUDECODE",
            self._claude_command, "-p", prompt,
            "--output-format", "stream-json",
            "--cwd", tmpdir,
        ]

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(output="", token_count=0, triggered=False, error="Timeout")

        if proc.returncode != 0:
            return ExecutionResult(
                output="", token_count=0, triggered=False,
                error=f"Exit code {proc.returncode}: {proc.stderr[:200] if proc.stderr else 'unknown'}",
            )

        return self._parse_stream_json(proc.stdout, skill_name)

    def _parse_stream_json(self, raw: str, skill_name: str) -> ExecutionResult:
        text_parts: list[str] = []
        triggered = False
        token_count = 0

        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")

            if event_type == "content_block_start":
                block = event.get("content_block", {})
                if block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input", {})
                    if name == "Skill" and skill_name in str(inp):
                        triggered = True
                    if name == "Read" and skill_name in str(inp):
                        triggered = True

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text_parts.append(delta.get("text", ""))

            elif event_type == "message_stop":
                usage = event.get("usage", {})
                token_count = usage.get("output_tokens", 0)

        output = "".join(text_parts)
        if token_count == 0 and output:
            token_count = int(len(output.split()) * 1.3)

        return ExecutionResult(
            output=output,
            token_count=token_count,
            triggered=triggered,
            error=None,
        )

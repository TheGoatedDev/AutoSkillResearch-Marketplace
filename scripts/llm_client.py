"""Local LLM client for hypothesis generation and judging via OpenAI-compatible API."""

import json
import re
from dataclasses import dataclass

import httpx


@dataclass
class HypothesisResult:
    hypothesis: str
    new_skill_content: str


@dataclass
class JudgeResult:
    winner: str  # "A", "B", or "draw"
    reasoning: str


def _extract_json(text: str) -> dict:
    """Extract JSON from text, handling markdown code fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")


class LocalLLMClient:
    def __init__(self, base_url: str, model: str, timeout: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def _chat(self, system: str, user: str) -> str:
        """Send a chat completion request and return the response text."""
        response = self._client.post(
            f"{self._base_url}/chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.7,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def generate_hypothesis(
        self,
        skill_content: str,
        experiment_log: dict,
        program_strategy: str,
        eval_cases: list[dict],
        optimize_hints: str | None = None,
    ) -> HypothesisResult:
        system = (
            "You are a skill optimization engine. You analyze skill instructions and propose "
            "ONE focused improvement per iteration.\n\n"
            f"## Optimization Strategy\n\n{program_strategy}\n\n"
            "## Rules\n"
            "- Make ONE focused change, not multiple.\n"
            "- Write a clear hypothesis BEFORE showing the edit.\n"
            "- Do NOT remove error handling sections.\n"
            "- Do NOT optimize for conciseness at the expense of completeness.\n\n"
            "## Output Format\n"
            "Respond with a JSON object (no other text):\n"
            '{"hypothesis": "what you changed and why", "new_skill_content": "full updated SKILL.md"}'
        )

        recent_entries = experiment_log.get("entries", [])[-10:]
        log_summary = json.dumps(recent_entries, indent=2) if recent_entries else "No prior iterations."

        user = (
            f"## Current SKILL.md\n\n{skill_content}\n\n"
            f"## Experiment Log (last 10 entries)\n\n{log_summary}\n\n"
            f"## Eval Cases\n\n{json.dumps(eval_cases, indent=2)}\n\n"
        )
        if optimize_hints:
            user += f"## Skill-Specific Optimization Hints\n\n{optimize_hints}\n\n"

        user += "Propose ONE focused change. Respond with JSON only."

        raw = self._chat(system, user)
        data = _extract_json(raw)

        if "hypothesis" not in data or "new_skill_content" not in data:
            raise ValueError("Could not parse hypothesis response: missing required fields")

        return HypothesisResult(
            hypothesis=data["hypothesis"],
            new_skill_content=data["new_skill_content"],
        )

    def judge(
        self,
        response_a: str,
        response_b: str,
        rubric: str,
    ) -> JudgeResult:
        system = (
            "You are an impartial judge comparing two AI assistant responses. "
            "You receive two responses (labeled 'Response A' and 'Response B') and a rubric "
            "describing what a good response looks like. You must pick a winner or declare a draw.\n\n"
            "Evaluate both responses against the rubric. Consider:\n"
            "1. Does the response follow the rubric's requirements?\n"
            "2. Is the response accurate and helpful?\n"
            "3. Is the response well-structured and clear?\n"
            "4. Does the response avoid the rubric's stated anti-patterns?\n\n"
            "You MUST NOT consider:\n"
            "- Response length (unless the rubric specifically mentions it)\n"
            "- Formatting preferences (unless the rubric specifically mentions it)\n"
            "- Your own opinions about what a good response looks like — only the rubric matters\n\n"
            "Respond with ONLY a JSON object:\n"
            '{"winner": "A", "reasoning": "..."}\n'
            'or {"winner": "B", "reasoning": "..."}\n'
            'or {"winner": "draw", "reasoning": "..."}'
        )

        user = (
            f"## Response A\n\n{response_a}\n\n"
            f"## Response B\n\n{response_b}\n\n"
            f"## Rubric\n\n{rubric}"
        )

        raw = self._chat(system, user)
        data = _extract_json(raw)

        winner = data.get("winner", "")
        if winner not in ("A", "B", "draw"):
            raise ValueError(f"Invalid winner value: {winner!r}")

        return JudgeResult(winner=winner, reasoning=data.get("reasoning", ""))

import json
import httpx
import pytest
import respx
from scripts.llm_client import LocalLLMClient, HypothesisResult, JudgeResult


BASE_URL = "http://localhost:1234/v1"
MODEL = "test-model"


class TestGenerateHypothesis:
    def _make_client(self) -> LocalLLMClient:
        return LocalLLMClient(base_url=BASE_URL, model=MODEL, timeout=30)

    @respx.mock
    def test_returns_hypothesis_and_content(self):
        response_json = {
            "hypothesis": "Add explicit trigger phrases",
            "new_skill_content": "---\nname: test\n---\nNew content",
        }
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps(response_json)}}],
            })
        )
        client = self._make_client()
        result = client.generate_hypothesis(
            skill_content="old content",
            experiment_log={"entries": []},
            program_strategy="Try instruction clarity first.",
            eval_cases=[{"id": "c1", "input": "hello", "rubric": "greet"}],
        )
        assert isinstance(result, HypothesisResult)
        assert result.hypothesis == "Add explicit trigger phrases"
        assert "New content" in result.new_skill_content

    @respx.mock
    def test_handles_json_in_code_fences(self):
        raw = '```json\n{"hypothesis": "test hyp", "new_skill_content": "new"}\n```'
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": raw}}],
            })
        )
        client = self._make_client()
        result = client.generate_hypothesis(
            skill_content="old", experiment_log={"entries": []},
            program_strategy="strategy", eval_cases=[],
        )
        assert result.hypothesis == "test hyp"

    @respx.mock
    def test_raises_on_malformed_response(self):
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": "not json at all"}}],
            })
        )
        client = self._make_client()
        with pytest.raises(ValueError, match="parse"):
            client.generate_hypothesis(
                skill_content="old", experiment_log={"entries": []},
                program_strategy="strategy", eval_cases=[],
            )


class TestJudge:
    def _make_client(self) -> LocalLLMClient:
        return LocalLLMClient(base_url=BASE_URL, model=MODEL, timeout=30)

    @respx.mock
    def test_returns_winner_and_reasoning(self):
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps({"winner": "A", "reasoning": "A was better"})}}],
            })
        )
        client = self._make_client()
        result = client.judge(response_a="resp A", response_b="resp B", rubric="be helpful")
        assert isinstance(result, JudgeResult)
        assert result.winner == "A"
        assert result.reasoning == "A was better"

    @respx.mock
    def test_accepts_draw(self):
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps({"winner": "draw", "reasoning": "equal"})}}],
            })
        )
        client = self._make_client()
        result = client.judge(response_a="a", response_b="b", rubric="rubric")
        assert result.winner == "draw"

    @respx.mock
    def test_raises_on_invalid_winner(self):
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps({"winner": "C", "reasoning": "invalid"})}}],
            })
        )
        client = self._make_client()
        with pytest.raises(ValueError, match="winner"):
            client.judge(response_a="a", response_b="b", rubric="rubric")

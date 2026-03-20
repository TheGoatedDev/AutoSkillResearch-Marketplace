from pathlib import Path
from scripts.config_loader import load_config, Config


class TestLoadConfig:
    def _write_yaml(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "config.yaml"
        p.write_text(content)
        return p

    def test_loads_defaults_from_yaml(self, tmp_path):
        yaml_path = self._write_yaml(tmp_path, """
local_llm:
  base_url: "http://localhost:9999/v1"
  model: "test-model"
  timeout: 60
cloud:
  claude_command: "my-claude"
  execution_timeout: 90
defaults:
  iterations_per_rotation: 5
  max_consecutive_errors: 2
""")
        config = load_config(config_path=yaml_path)
        assert config.local_llm_base_url == "http://localhost:9999/v1"
        assert config.local_llm_model == "test-model"
        assert config.local_llm_timeout == 60
        assert config.claude_command == "my-claude"
        assert config.execution_timeout == 90
        assert config.iterations_per_rotation == 5
        assert config.max_consecutive_errors == 2

    def test_cli_overrides_yaml(self, tmp_path):
        yaml_path = self._write_yaml(tmp_path, """
local_llm:
  base_url: "http://localhost:1234/v1"
  model: "default-model"
  timeout: 120
cloud:
  claude_command: "claude"
  execution_timeout: 120
defaults:
  iterations_per_rotation: 10
  max_consecutive_errors: 3
""")
        config = load_config(
            config_path=yaml_path,
            cli_model="override-model",
            cli_base_url="http://other:5555/v1",
            cli_iterations=3,
        )
        assert config.local_llm_model == "override-model"
        assert config.local_llm_base_url == "http://other:5555/v1"
        assert config.iterations_per_rotation == 3
        assert config.claude_command == "claude"

    def test_uses_hardcoded_defaults_when_no_yaml(self, tmp_path):
        config = load_config(config_path=tmp_path / "nonexistent.yaml")
        assert config.local_llm_base_url == "http://localhost:1234/v1"
        assert config.local_llm_model == "qwen3-coder"
        assert config.iterations_per_rotation == 10

    def test_partial_yaml_fills_missing_with_defaults(self, tmp_path):
        yaml_path = self._write_yaml(tmp_path, """
local_llm:
  model: "custom-model"
""")
        config = load_config(config_path=yaml_path)
        assert config.local_llm_model == "custom-model"
        assert config.local_llm_base_url == "http://localhost:1234/v1"
        assert config.iterations_per_rotation == 10

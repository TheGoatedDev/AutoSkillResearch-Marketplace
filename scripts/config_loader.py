"""Config loading with YAML defaults and CLI overrides."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Config:
    local_llm_base_url: str
    local_llm_model: str
    local_llm_timeout: int
    claude_command: str
    execution_timeout: int
    iterations_per_rotation: int
    max_consecutive_errors: int
    skill: str | None = None
    dry_run: bool = False


_DEFAULTS = {
    "local_llm": {
        "base_url": "http://localhost:1234/v1",
        "model": "qwen3-coder",
        "timeout": 120,
    },
    "cloud": {
        "claude_command": "claude",
        "execution_timeout": 120,
    },
    "defaults": {
        "iterations_per_rotation": 10,
        "max_consecutive_errors": 3,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    config_path: Path | None = None,
    cli_model: str | None = None,
    cli_base_url: str | None = None,
    cli_iterations: int | None = None,
    cli_skill: str | None = None,
    cli_dry_run: bool = False,
) -> Config:
    file_config: dict = {}
    if config_path and config_path.exists():
        file_config = yaml.safe_load(config_path.read_text()) or {}

    merged = _deep_merge(_DEFAULTS, file_config)

    llm = merged["local_llm"]
    cloud = merged["cloud"]
    defaults = merged["defaults"]

    return Config(
        local_llm_base_url=cli_base_url or llm["base_url"],
        local_llm_model=cli_model or llm["model"],
        local_llm_timeout=llm["timeout"],
        claude_command=cloud["claude_command"],
        execution_timeout=cloud["execution_timeout"],
        iterations_per_rotation=cli_iterations or defaults["iterations_per_rotation"],
        max_consecutive_errors=defaults["max_consecutive_errors"],
        skill=cli_skill,
        dry_run=cli_dry_run,
    )

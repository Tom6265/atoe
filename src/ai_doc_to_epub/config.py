from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    """Runtime configuration derived from environment variables."""

    llm_api_key: Optional[str] = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_output_tokens: int = 3500
    mineru_api_url: Optional[str] = None
    mineru_api_key: Optional[str] = None
    mineru_binary_path: Optional[Path] = None
    default_language: str = "en"
    workspace_dir: Path = Path(os.getenv("APP_WORKSPACE", "/tmp/ai-doc-to-epub"))

    def __post_init__(self) -> None:
        env = os.getenv
        self.llm_api_key = env("LLM_API_KEY", self.llm_api_key)
        self.llm_base_url = env("LLM_BASE_URL", self.llm_base_url)
        self.llm_model = env("LLM_MODEL", self.llm_model)
        self.llm_temperature = float(env("LLM_TEMPERATURE", str(self.llm_temperature)))
        self.llm_max_output_tokens = int(
            env("LLM_MAX_OUTPUT_TOKENS", str(self.llm_max_output_tokens))
        )
        self.mineru_api_url = env("MINERU_API_URL", self.mineru_api_url)
        self.mineru_api_key = env("MINERU_API_KEY", self.mineru_api_key)
        mineru_binary = env("MINERU_BINARY_PATH")
        if mineru_binary:
            self.mineru_binary_path = Path(mineru_binary)
        workspace = env("APP_WORKSPACE")
        if workspace:
            self.workspace_dir = Path(workspace)

    @cached_property
    def has_llm_credentials(self) -> bool:
        return bool(self.llm_api_key)

    @cached_property
    def has_mineru_remote(self) -> bool:
        return bool(self.mineru_api_url)

    @cached_property
    def has_mineru_local(self) -> bool:
        return (
            self.mineru_binary_path is not None
            and self.mineru_binary_path.expanduser().exists()
        )


SETTINGS = Settings()

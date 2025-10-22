from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict

from markdown import Markdown

try:  # pragma: no cover - openai is optional during testing
    from openai import OpenAI
except Exception:  # pragma: no cover - fallback when openai isn't installed
    OpenAI = None  # type: ignore

from .config import SETTINGS


class BaseLLMClient(ABC):
    """Base interface for LLM-powered markdown enhancement."""

    @abstractmethod
    def enhance(self, markdown_text: str, metadata: Dict[str, str]) -> str:
        """Return HTML that is ready for EPUB creation."""


@dataclass
class LocalFormatterLLM(BaseLLMClient):
    """Deterministic markdown-to-HTML formatter used when LLMs are unavailable."""

    heading_depth: int = 2

    def enhance(self, markdown_text: str, metadata: Dict[str, str]) -> str:
        md = Markdown(
            extensions=["extra", "toc", "footnotes", "tables"],
            extension_configs={"toc": {"toc_depth": self.heading_depth}},
        )
        body_html = md.convert(markdown_text)
        toc_html = getattr(md, "toc", "") or ""
        nav_html = f"<nav id='toc'>{toc_html}</nav>" if toc_html else ""
        html = (
            "<html><head><meta charset='utf-8'/></head>"
            f"<body>{nav_html}{body_html}</body></html>"
        )
        return html


@dataclass
class OpenAICompatibleLLM(BaseLLMClient):
    """Wrapper around OpenAI compatible chat completion APIs."""

    api_key: str
    base_url: str
    model: str
    temperature: float = 0.1
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if OpenAI is None:  # pragma: no cover - executed only if openai is unavailable
            raise RuntimeError(
                "openai package is not installed; cannot use OpenAICompatibleLLM"
            )
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def enhance(self, markdown_text: str, metadata: Dict[str, str]) -> str:
        system_prompt = (
            "You are an expert publishing assistant. Convert the provided Markdown "
            "document into clean, semantic HTML5 suitable for an EPUB chapter. "
            "Preserve headings hierarchy, tables, and inline formatting. "
            "Ensure footnotes become <aside> elements linked via anchors. "
            "Inject an ordered table of contents as a <nav> element at the top."
        )
        user_prompt = (
            "Metadata: {metadata}\n\nMarkdown source:\n\n{markdown}\n\n"
            "Return ONLY valid HTML within <html> tags."
        ).format(metadata=metadata, markdown=markdown_text)

        response = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = response.choices[0]
        html = choice.message.content if choice.message else None
        if not html:
            raise RuntimeError("LLM returned an empty response")
        return html


def build_llm_client(use_local_formatter: bool = False) -> BaseLLMClient:
    if use_local_formatter:
        return LocalFormatterLLM()
    if SETTINGS.has_llm_credentials:
        try:
            return OpenAICompatibleLLM(
                api_key=SETTINGS.llm_api_key or "",  # type: ignore[arg-type]
                base_url=SETTINGS.llm_base_url,
                model=SETTINGS.llm_model,
                temperature=SETTINGS.llm_temperature,
                max_output_tokens=SETTINGS.llm_max_output_tokens,
            )
        except Exception:
            # fall back to local formatter when remote init fails
            return LocalFormatterLLM()
    return LocalFormatterLLM()

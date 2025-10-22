from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from .config import SETTINGS
from .epub_builder import EpubBuilder, EpubMetadata
from .llm_client import BaseLLMClient, build_llm_client
from .mineru_client import MinerUClient
from .models import ConversionRequest, ConversionResult


@dataclass
class PipelineConfig:
    output_dir: Path = SETTINGS.workspace_dir


class ConversionPipeline:
    """Coordinates document conversion into high-quality EPUB files."""

    def __init__(
        self,
        mineru_client: Optional[MinerUClient] = None,
        llm_client: Optional[BaseLLMClient] = None,
        epub_builder: Optional[EpubBuilder] = None,
        config: Optional[PipelineConfig] = None,
    ) -> None:
        self.mineru_client = mineru_client or MinerUClient()
        self.llm_client = llm_client or build_llm_client()
        self.epub_builder = epub_builder or EpubBuilder()
        self.config = config or PipelineConfig()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def convert(self, file_path: Path, request: ConversionRequest) -> ConversionResult:
        file_path = file_path.expanduser().resolve()
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        markdown_text = self.mineru_client.convert_to_markdown(file_path)
        llm_client = self.llm_client
        if request.use_local_formatter:
            llm_client = build_llm_client(use_local_formatter=True)

        html = llm_client.enhance(
            markdown_text,
            metadata={
                "title": request.title,
                "author": request.author,
                "language": request.language,
                "description": request.description or "",
            },
        )
        if "<html" not in html.lower():
            html = (
                "<html><head><meta charset='utf-8'/></head>"
                f"<body>{html}</body></html>"
            )
        if not request.annotate:
            html = self._strip_footnotes(html)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_epub_path = Path(tmpdir) / "book.epub"
            metadata = EpubMetadata(
                title=request.title,
                author=request.author,
                language=request.language or SETTINGS.default_language,
                description=request.description,
            )
            output_file = self.epub_builder.build(html, metadata, temp_epub_path)
            final_path = self._finalize_output(output_file, request)

        return ConversionResult(
            title=request.title,
            author=request.author,
            language=request.language,
            output_path=final_path,
            created_at=datetime.utcnow(),
            file_size=final_path.stat().st_size,
        )

    @staticmethod
    def _strip_footnotes(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for aside in soup.select("aside.footnote"):
            aside.decompose()
        for sup in soup.select("sup[id^='fnref']"):
            sup.unwrap()
        return str(soup)

    def _finalize_output(self, temp_file: Path, request: ConversionRequest) -> Path:
        safe_title = "-".join(part for part in request.title.split() if part)
        output_filename = f"{safe_title or 'book'}.epub"
        destination = self.config.output_dir / output_filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(temp_file.read_bytes())
        return destination

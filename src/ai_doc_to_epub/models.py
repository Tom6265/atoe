from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ConversionRequest(BaseModel):
    title: str = Field(..., description="Book title")
    author: str = Field(default="Unknown Author", description="Book author")
    language: str = Field(default="en", description="BCP47 language code")
    description: Optional[str] = Field(
        default=None, description="Short synopsis included in EPUB metadata"
    )
    annotate: bool = Field(
        default=True,
        description="Whether to preserve and render footnotes/annotations",
    )
    use_local_formatter: bool = Field(
        default=False,
        description=(
            "Disable remote LLM usage and rely on deterministic local formatting."
        ),
    )


class ConversionResult(BaseModel):
    title: str
    author: str
    language: str
    output_path: Path
    created_at: datetime
    file_size: int

    class Config:
        arbitrary_types_allowed = True

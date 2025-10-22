from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import httpx
from docx import Document
from pdfminer.high_level import extract_text

from .config import SETTINGS


class MinerUError(RuntimeError):
    """Errors raised during MinerU conversion."""


class MinerUClient:
    """Client wrapper capable of talking to MinerU over HTTP or CLI.

    Falls back to lightweight in-process extractors when MinerU is unavailable.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        binary_path: Optional[Path] = None,
    ) -> None:
        self.api_url = api_url or SETTINGS.mineru_api_url
        self.api_key = api_key or SETTINGS.mineru_api_key
        resolved_binary = binary_path or SETTINGS.mineru_binary_path
        if isinstance(resolved_binary, str):
            resolved_binary = Path(resolved_binary)
        if resolved_binary is None:
            detected = shutil.which("mineru")
            resolved_binary = Path(detected) if detected else None
        self.binary_path = resolved_binary

    def convert_to_markdown(self, input_path: Path) -> str:
        input_path = input_path.expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Document does not exist: {input_path}")

        if self.api_url:
            return self._convert_via_http(input_path)
        if self._has_binary():
            return self._convert_via_cli(input_path)
        return self._fallback_extract(input_path)

    # ------------------------------------------------------------------
    # Remote HTTP integration
    # ------------------------------------------------------------------
    def _convert_via_http(self, input_path: Path) -> str:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=300.0) as client:
            with input_path.open("rb") as file_handle:
                files = {"file": (input_path.name, file_handle)}
                response = client.post(
                    f"{self.api_url.rstrip('/')}/convert", files=files, headers=headers
                )
        if response.status_code >= 400:
            raise MinerUError(
                f"MinerU HTTP conversion failed ({response.status_code}): {response.text}"
            )

        data = response.json()
        if "markdown" in data:
            return data["markdown"]
        if "content" in data:
            return data["content"]
        raise MinerUError(
            "MinerU HTTP response did not contain a 'markdown' or 'content' field."
        )

    # ------------------------------------------------------------------
    # Local CLI integration
    # ------------------------------------------------------------------
    def _has_binary(self) -> bool:
        return bool(self.binary_path and self.binary_path.exists())

    def _convert_via_cli(self, input_path: Path) -> str:
        assert self.binary_path is not None
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            command = [
                str(self.binary_path),
                "convert",
                str(input_path),
                "--output",
                str(output_path),
                "--format",
                "markdown",
            ]
            process = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            if process.returncode != 0:
                raise MinerUError(
                    "MinerU CLI failed with code {code}: {stderr}".format(
                        code=process.returncode, stderr=process.stderr.strip()
                    )
                )
            if not output_path.exists():
                raise MinerUError(
                    "MinerU CLI conversion succeeded but no output file was produced."
                )
            content = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(content, dict) and "markdown" in content:
                return content["markdown"]
            if isinstance(content, str):
                return content
            raise MinerUError("Unexpected MinerU CLI output structure")

    # ------------------------------------------------------------------
    # Lightweight fallback extractors
    # ------------------------------------------------------------------
    def _fallback_extract(self, input_path: Path) -> str:
        suffix = input_path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(input_path)
        if suffix == ".docx":
            return self._extract_docx(input_path)
        if suffix == ".doc":
            raise MinerUError(
                "Legacy .doc files require MinerU integration; install MinerU to enable support."
            )
        raise MinerUError(
            f"Unsupported input format '{suffix}'. Provide a PDF or Word document."
        )

    @staticmethod
    def _extract_pdf(input_path: Path) -> str:
        try:
            text = extract_text(str(input_path))
        except Exception as exc:  # pragma: no cover - pdfminer raises many subclasses
            raise MinerUError(f"Fallback PDF extraction failed: {exc}") from exc
        return text.strip()

    @staticmethod
    def _extract_docx(input_path: Path) -> str:
        try:
            document = Document(str(input_path))
        except Exception as exc:  # pragma: no cover - python-docx errors depend on file
            raise MinerUError(f"Fallback DOCX extraction failed: {exc}") from exc
        parts = []
        for paragraph in document.paragraphs:
            parts.append(paragraph.text.strip())
        return "\n\n".join(part for part in parts if part)

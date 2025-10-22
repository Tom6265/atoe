from __future__ import annotations

from pathlib import Path

from ai_doc_to_epub.epub_builder import EpubBuilder, EpubMetadata


def test_epub_builder_creates_file(tmp_path: Path) -> None:
    builder = EpubBuilder()
    metadata = EpubMetadata(title="Sample", author="Tester", language="en")
    html = """
    <html><body>
    <h1>Chapter 1</h1>
    <p>Content paragraph.</p>
    <h1>Chapter 2</h1>
    <p>Another paragraph.</p>
    </body></html>
    """

    output_path = tmp_path / "output.epub"
    result = builder.build(html, metadata, output_path)

    assert result.exists()
    assert result.suffix == ".epub"
    assert result.stat().st_size > 0

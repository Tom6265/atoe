from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from bs4 import BeautifulSoup
from ebooklib import epub


@dataclass
class Chapter:
    title: str
    filename: str
    content: str


def _sanitize_filename(name: str) -> str:
    slug = "-".join(part for part in name.split() if part)
    return f"{slug.lower() or 'chapter'}-{uuid.uuid4().hex[:8]}.xhtml"


def _split_html_into_chapters(html: str) -> List[Chapter]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup

    chapters: List[Chapter] = []
    current_title = "Introduction"
    current_nodes: List[str] = []

    def flush_chapter(title: str, nodes: Iterable[str]) -> None:
        markup = "".join(nodes).strip()
        if not markup:
            return
        chapters.append(
            Chapter(title=title, filename=_sanitize_filename(title), content=markup)
        )

    for node in body.children:
        if getattr(node, "name", None) and node.name.startswith("h1"):
            flush_chapter(current_title, current_nodes)
            current_title = node.get_text(strip=True) or "Untitled"
            current_nodes = [str(node)]
        else:
            current_nodes.append(str(node))

    flush_chapter(current_title, current_nodes)

    if not chapters:
        chapters.append(
            Chapter(
                title="Document",
                filename=_sanitize_filename("document"),
                content=str(body),
            )
        )
    return chapters


@dataclass
class EpubMetadata:
    title: str
    author: str = "Unknown"
    language: str = "en"
    description: str | None = None


class EpubBuilder:
    """Compose a styled EPUB document from HTML."""

    def __init__(self) -> None:
        self._stylesheet = self._default_stylesheet()

    def build(self, html: str, metadata: EpubMetadata, output_path: Path) -> Path:
        chapters = _split_html_into_chapters(html)

        book = epub.EpubBook()
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(metadata.title)
        book.set_language(metadata.language)
        book.add_author(metadata.author)
        book.add_metadata(
            "DC", "date", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        if metadata.description:
            book.add_metadata("DC", "description", metadata.description)

        style_item = epub.EpubItem(
            uid="style",
            file_name="styles/stylesheet.css",
            media_type="text/css",
            content=self._stylesheet.encode("utf-8"),
        )
        book.add_item(style_item)

        epub_chapters: List[epub.EpubHtml] = []
        toc: List[Tuple[epub.EpubHtml, List[epub.Link]]] = []

        for chapter in chapters:
            epub_chapter = epub.EpubHtml(
                title=chapter.title,
                file_name=f"text/{chapter.filename}",
                lang=metadata.language,
            )
            epub_chapter.content = (
                "<?xml version='1.0' encoding='utf-8'?>"
                "<!DOCTYPE html>"
                f"<html xmlns='http://www.w3.org/1999/xhtml'>"
                f"<head><title>{chapter.title}</title><link rel='stylesheet' href='../styles/stylesheet.css'/></head>"
                f"<body>{chapter.content}</body></html>"
            )
            book.add_item(epub_chapter)
            epub_chapters.append(epub_chapter)

        for chapter in epub_chapters:
            toc.append(chapter)

        book.toc = tuple(toc)

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        book.spine = ["nav", *epub_chapters]

        output_path = output_path.with_suffix(".epub")
        book.write_epub(str(output_path))
        return output_path

    @staticmethod
    def _default_stylesheet() -> str:
        return """
        body {
            font-family: "Noto Serif", Georgia, serif;
            line-height: 1.5;
            margin: 1em;
        }
        h1, h2, h3, h4 {
            font-family: "Noto Sans", Arial, sans-serif;
            margin-top: 1.4em;
        }
        nav#toc {
            margin-bottom: 2em;
            padding: 1em;
            border: 1px solid #dddddd;
            background: #f9f9f9;
        }
        aside.footnote {
            font-size: 0.9em;
            border-top: 1px solid #cccccc;
            margin-top: 0.5em;
            padding-top: 0.5em;
        }
        table {
            border-collapse: collapse;
            width: 100%;
        }
        table, th, td {
            border: 1px solid #cccccc;
        }
        th, td {
            padding: 0.5em;
        }
        """

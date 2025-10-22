from __future__ import annotations

import sys
from pathlib import Path

import typer

from .models import ConversionRequest
from .pipeline import ConversionPipeline

app = typer.Typer(help="Convert PDF and Word documents into polished EPUB files.")


@app.command()
def convert(
    file_path: Path = typer.Argument(..., help="Path to the PDF or Word document."),
    title: str = typer.Option(..., "--title", "-t", help="Title for the EPUB."),
    author: str = typer.Option("Unknown Author", "--author", "-a", help="Author name."),
    language: str = typer.Option("en", "--language", "-l", help="Language code."),
    description: str | None = typer.Option(None, help="Short description for metadata."),
    local_formatter: bool = typer.Option(
        False,
        "--local-formatter",
        help="Use deterministic local HTML formatter instead of calling an LLM.",
    ),
) -> None:
    """Convert a document and print the resulting EPUB path."""
    if not file_path.exists():
        typer.secho(f"Input file not found: {file_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    suffix = file_path.suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx"}:
        typer.secho("Only PDF and Word documents are supported.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    pipeline = ConversionPipeline()
    request = ConversionRequest(
        title=title,
        author=author,
        language=language,
        description=description,
        use_local_formatter=local_formatter,
    )
    result = pipeline.convert(file_path, request)
    typer.secho(f"EPUB created at: {result.output_path}", fg=typer.colors.GREEN)


@app.command()
def runserver(
    host: str = typer.Option("0.0.0.0", help="Binding interface."),
    port: int = typer.Option(8000, help="Application port."),
    reload: bool = typer.Option(False, help="Enable auto reload for development."),
) -> None:
    """Start the FastAPI server."""
    try:
        import uvicorn
    except ImportError:  # pragma: no cover - uvicorn is a runtime dependency
        typer.secho("uvicorn is not installed.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    from .app import app as fastapi_app

    uvicorn.run(fastapi_app, host=host, port=port, reload=reload)




def main() -> None:
    app()


if __name__ == "__main__":
    main()

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .mineru_client import MinerUError
from .models import ConversionRequest
from .pipeline import ConversionPipeline

app = FastAPI(title="AI Document to EPUB Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/convert")
async def convert_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form("Unknown Author"),
    language: str = Form("en"),
    description: str | None = Form(default=None),
    annotate: bool = Form(default=True),
    use_local_formatter: bool = Form(default=False),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx"}:
        return JSONResponse(
            status_code=400,
            content={"detail": "Only PDF and Word documents are supported."},
        )

    pipeline = ConversionPipeline()
    request = ConversionRequest(
        title=title,
        author=author,
        language=language,
        description=description,
        annotate=annotate,
        use_local_formatter=use_local_formatter,
    )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_input:
        content = await file.read()
        temp_input.write(content)
        temp_input_path = Path(temp_input.name)

    try:
        result = pipeline.convert(temp_input_path, request)
    except MinerUError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime safety net
        raise HTTPException(status_code=500, detail="Conversion failed") from exc
    finally:
        temp_input_path.unlink(missing_ok=True)

    return FileResponse(
        path=result.output_path,
        media_type="application/epub+zip",
        filename=result.output_path.name,
    )

"""Ingestion: PDF (PyMuPDF), DOCX, URL (httpx + BeautifulSoup), chunking, MongoDB."""
from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from typing import Literal

import httpx
from bs4 import BeautifulSoup

from ..config import get_settings
from .url_safety import validate_public_http_url

logger = logging.getLogger("helix.ingestion")


@dataclass
class IngestSource:
    kind: Literal["text", "bytes", "url"]
    text: str | None = None
    filename: str | None = None
    data: bytes | None = None
    url: str | None = None


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf_pymupdf(data: bytes) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    parts: list[str] = []
    for page in doc:
        parts.append(page.get_text() or "")
    doc.close()
    return "\n".join(parts).strip()


def extract_text_from_docx(data: bytes) -> str:
    from docx import Document

    d = Document(io.BytesIO(data))
    return "\n".join(p.text for p in d.paragraphs).strip()


async def extract_text_from_url(url: str, timeout: float = 30.0) -> str:
    safe_url = validate_public_http_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; HelixIngest/1.0; +https://example.invalid)"
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(safe_url, headers=headers)
        resp.raise_for_status()
        ctype = (resp.headers.get("content-type") or "").lower()
        raw = resp.content
    if "pdf" in ctype or safe_url.lower().endswith(".pdf"):
        return extract_text_from_pdf_pymupdf(raw)
    if "word" in ctype or safe_url.lower().endswith(".docx"):
        return extract_text_from_docx(raw)
    html = raw.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return _clean_text(soup.get_text("\n"))


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf_pymupdf(data)
    if name.endswith(".docx"):
        return extract_text_from_docx(data)
    return data.decode("utf-8", errors="ignore").strip()


async def extract_text(source: IngestSource) -> str:
    if source.kind == "text":
        return _clean_text(source.text or "")
    if source.kind == "bytes":
        return _clean_text(
            extract_text_from_bytes(source.filename or "upload.bin", source.data or b"")
        )
    if source.kind == "url":
        return _clean_text(await extract_text_from_url(source.url or ""))
    return ""


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 120) -> list[str]:
    text = _clean_text(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_chars)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks or [text[:max_chars]]


async def store_chunks_mongo(
    project_id: str, chunks: list[str]
) -> int:
    settings = get_settings()
    url = (settings.mongo_url or "").strip()
    if not url:
        return 0
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except Exception:
        return 0
    client = None
    try:
        client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=2000)
        db = client.get_default_database()
        col = db["ingestion_chunks"]
        await col.delete_many({"project_id": project_id})
        docs = [
            {
                "project_id": project_id,
                "chunk_index": i,
                "text": t,
            }
            for i, t in enumerate(chunks)
        ]
        if docs:
            await col.insert_many(docs)
        return len(docs)
    except Exception as exc:
        logger.warning("Mongo chunk store skipped for %s: %s", project_id, exc)
        return 0
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


async def extract_clean_chunk_and_store(
    source: IngestSource, project_id: str
) -> tuple[str, list[str], int]:
    raw = await extract_text(source)
    cleaned = _clean_text(raw)
    chunks = chunk_text(cleaned)
    inserted = await store_chunks_mongo(project_id, chunks)
    return cleaned, chunks, inserted


def extract_text_sync_for_celery(source: IngestSource) -> str:
    """Sync entry for Celery workers (no running event loop)."""
    import asyncio

    if source.kind == "url":
        return asyncio.run(extract_text(source))
    if source.kind == "text":
        return _clean_text(source.text or "")
    return _clean_text(
        extract_text_from_bytes(source.filename or "upload.bin", source.data or b"")
    )

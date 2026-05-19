"""Sentence embeddings + per-project FAISS retrieval."""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger("helix.rag")

_Model = None
_Indexes: Dict[str, Tuple["faiss.IndexFlatIP", np.ndarray, List[str]]] = {}


def _get_model():
    global _Model
    if _Model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _Model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:  # pragma: no cover
            logger.warning("sentence-transformers unavailable: %s", exc)
            _Model = False  # type: ignore
    return _Model if _Model is not False else None


def _get_faiss():
    try:
        import faiss

        return faiss
    except Exception as exc:  # pragma: no cover
        logger.warning("faiss unavailable: %s", exc)
        return None


def embed_requirements(project_id: str, texts: List[str]) -> None:
    """Build / replace the in-memory index for a project from requirement chunks."""
    model = _get_model()
    faiss = _get_faiss()
    if model is None or faiss is None:
        return
    chunks = [t.strip() for t in texts if t and t.strip()]
    if not chunks:
        _Indexes.pop(project_id, None)
        return
    vectors = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
    mat = np.asarray(vectors, dtype="float32")
    dim = mat.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(mat)
    _Indexes[project_id] = (index, mat, chunks)


def search(query: str, project_id: str, *, top_k: int = 5) -> List[str]:
    """Return up to `top_k` most similar requirement chunks for the query."""
    model = _get_model()
    faiss = _get_faiss()
    if model is None or faiss is None:
        return []
    bucket = _Indexes.get(project_id)
    if bucket is None:
        return []
    index, _mat, chunks = bucket
    q = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    qv = np.asarray(q, dtype="float32")
    _scores, idxs = index.search(qv, min(top_k, len(chunks)))
    out: List[str] = []
    for rank in idxs[0]:
        if rank < 0 or rank >= len(chunks):
            continue
        out.append(chunks[int(rank)])
    return out[:top_k]

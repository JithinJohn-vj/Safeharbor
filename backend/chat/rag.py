"""
RAG over curated legal excerpts (markdown files). Uses Chroma persistent store.
Run: python manage.py ingest_legal_docs
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_COLLECTION = "safeharbor_legal"


def get_collection():
    try:
        import chromadb
        from django.conf import settings
    except ImportError:
        return None

    path = Path(str(getattr(settings, "CHROMA_PATH", os.environ.get("CHROMA_PATH", ".chroma_data"))))
    Path(path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(path))
    return client.get_or_create_collection(
        name=_COLLECTION,
        metadata={"description": "EU/UK gambling law excerpts"},
    )


def retrieve_relevant_chunks(query: str, n: int = 4) -> str:
    if not query or not query.strip():
        return ""
    col = get_collection()
    if col is None:
        return ""
    try:
        try:
            count = col.count()
        except Exception:
            count = 0
        if count == 0:
            return ""
        res = col.query(
            query_texts=[query[:2000]],
            n_results=min(n, max(1, count)),
        )
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        parts = []
        for doc, meta in zip(docs, metas):
            src = ""
            if isinstance(meta, dict):
                src = meta.get("source", "")
            parts.append(f"[Source: {src}]\n{doc}")
        return "\n\n---\n\n".join(parts) if parts else ""
    except Exception as e:
        logger.warning("RAG query failed: %s", e)
        return ""

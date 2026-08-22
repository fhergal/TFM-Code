"""Retriever de respaldo, sin embeddings ni vector store, para el "modo
demo" de la UI (ver README.md): permite ejecutar el agente de bastanteo
completo (04_src/agent/) sin depender de llama-index/ChromaDB ni de
descargar ningun modelo -- util cuando esas dependencias pesadas no estan
instaladas (p. ej. portatil recien clonado, o el propio sandbox de
desarrollo de esta sesion, donde la instalacion de chromadb no llego a
completarse por limitaciones de red).

No pretende ser un sustituto serio del retriever semantico de
`rag/index_store.py` -- es deliberadamente simple (solapamiento de
palabras) para no tener dependencias. En la memoria del TFM debe quedar
claro que el retrieval real evaluado es el de `rag/`, no este.
"""

from __future__ import annotations

import re
from typing import Any, Callable

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text or "")}


def _flatten_blocks(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Aplana document_inventory[].pages[].blocks[] a "citas" con la misma
    forma que devuelve rag.query(), para que el agente no note la
    diferencia entre este retriever y el semantico real."""
    flat = []
    for document in case.get("document_inventory", []):
        document_id = document.get("document_id")
        for page in document.get("pages", []):
            page_number = page.get("page_number")
            for block in page.get("blocks", []):
                flat.append(
                    {
                        "chunk_id": block.get("block_id"),
                        "text": block.get("text", ""),
                        "document_id": document_id,
                        "page_number": page_number,
                        "section": (block.get("semantics") or {}).get("section"),
                        "block_ids": [block.get("block_id")],
                        "bbox": block.get("bbox"),
                    }
                )
    return flat


def build_naive_retriever(case: dict[str, Any]) -> Callable[[str, int], list[dict[str, Any]]]:
    """Construye un `retrieve_fn` (misma firma que espera
    `agent.run_bastanteo`) que puntua cada bloque del caso por solapamiento
    de tokens (Jaccard) con la query, sin ningun modelo de embeddings."""
    blocks = _flatten_blocks(case)

    def _retrieve(query: str, top_k: int) -> list[dict[str, Any]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for block in blocks:
            block_tokens = _tokenize(block["text"])
            if not block_tokens:
                continue
            overlap = query_tokens & block_tokens
            union = query_tokens | block_tokens
            score = len(overlap) / len(union) if union else 0.0
            if score > 0:
                scored.append({**block, "score": score})

        scored.sort(key=lambda c: c["score"], reverse=True)
        return scored[:top_k]

    return _retrieve

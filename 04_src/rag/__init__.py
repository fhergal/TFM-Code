"""
Modulo rag: chunking layout-aware + indexacion/retrieval con LlamaIndex y
ChromaDB (ver Hilo 04, decision 3 y 5).

No debe (ver README.md): implementar logica de agente conversacional
compleja -- eso vive en 04_src/agent/, que consume `query()` como
herramienta/servicio.

Uso tipico:

    from normalizer import build_document_entry
    from rag import build_chunks, build_nodes, build_index, query

    doc = build_document_entry(parser_result, document_id="DOC-0001", document_type_pred="solicitud")
    chunks = build_chunks(doc, case_id="EXP-2026-0001")
    nodes = build_nodes(chunks)
    index = build_index(nodes)

    citas = query(index, "Consta el DNI del solicitante?", top_k=3)
"""

from .chunking import build_chunks
from .index_store import build_index, build_nodes, query

__all__ = ["build_chunks", "build_nodes", "build_index", "query"]

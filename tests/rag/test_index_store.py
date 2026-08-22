"""Tests de index_store.build_nodes/build_index/query.

Requieren llama-index-core, llama-index-vector-stores-chroma y chromadb
instalados (ver pyproject.toml). Usan MockEmbedding (vectores deterministas,
sin red) y un cliente Chroma efimero en tmp_path, para no depender de
descargar el modelo real de embeddings ni de red.

NOTA: no se ha podido ejecutar esta suite en el entorno sandbox de esta
sesion porque la instalacion de las dependencias pesadas (chromadb/
onnxruntime, llama-index-core) no ha llegado a completarse (ver aviso en
el chat). Ejecutar `pytest tests/rag/ -v` en local, con
`pip install -e ".[dev]"`, para una verificacion completa.
"""

from __future__ import annotations

import pytest

from rag.chunking import build_chunks


def _document():
    return {
        "document_id": "DOC-0001",
        "pages": [
            {
                "page_number": 1,
                "blocks": [
                    {
                        "block_id": "b1",
                        "block_type": "paragraph",
                        "text": "El solicitante declara un DNI 12345678A.",
                        "bbox": {"x0": 0, "y0": 0, "x1": 100, "y1": 20, "unit": "pixel"},
                        "semantics": {"section": "datos_solicitante"},
                    },
                    {
                        "block_id": "b2",
                        "block_type": "paragraph",
                        "text": "Motivo de la solicitud: revision de grado de discapacidad.",
                        "bbox": {"x0": 0, "y0": 25, "x1": 100, "y1": 45, "unit": "pixel"},
                        "semantics": {"section": "alegaciones"},
                    },
                ],
            }
        ],
    }


@pytest.fixture
def chunks():
    return build_chunks(_document(), case_id="EXP-2026-0001")


@pytest.fixture
def mock_embed_model():
    from llama_index.core.embeddings import MockEmbedding

    return MockEmbedding(embed_dim=8)


def test_build_nodes_preserves_text_and_metadata(chunks):
    from rag.index_store import build_nodes

    nodes = build_nodes(chunks)

    assert len(nodes) == len(chunks)
    assert nodes[0].node_id == chunks[0]["chunk_id"]
    assert nodes[0].metadata["document_id"] == "DOC-0001"
    assert nodes[0].metadata["section"] == "datos_solicitante"


def test_build_index_and_query_returns_traceable_citations(tmp_path, chunks, mock_embed_model):
    from rag.index_store import build_index, build_nodes, query

    nodes = build_nodes(chunks)
    index = build_index(
        nodes,
        persist_dir=tmp_path / "chroma",
        collection_name="test_collection",
        embed_model=mock_embed_model,
    )

    results = query(index, "DNI del solicitante", top_k=2)

    assert len(results) <= 2
    assert len(results) > 0
    first = results[0]
    for key in ("chunk_id", "score", "text", "document_id", "page_number", "section", "block_ids", "bbox"):
        assert key in first
    assert first["document_id"] == "DOC-0001"


def test_build_index_persists_across_reopen(tmp_path, chunks, mock_embed_model):
    """El indice debe sobrevivir a un reinicio del proceso (persistencia real
    en disco), no solo vivir en memoria durante la sesion actual."""
    import chromadb
    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.vector_stores.chroma import ChromaVectorStore

    from rag.index_store import build_index, build_nodes

    persist_dir = tmp_path / "chroma"
    nodes = build_nodes(chunks)
    build_index(
        nodes,
        persist_dir=persist_dir,
        collection_name="persisted",
        embed_model=mock_embed_model,
    )

    # Reabrir como si fuera un proceso nuevo, sin volver a indexar nodes.
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection("persisted")
    assert collection.count() == len(nodes)

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    reopened = VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context, embed_model=mock_embed_model
    )
    results = reopened.as_retriever(similarity_top_k=1).retrieve("discapacidad")
    assert len(results) == 1

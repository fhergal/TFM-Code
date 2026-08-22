"""Indexación y retrieval sobre ChromaDB usando LlamaIndex (decision del
Hilo 04: LlamaIndex para ingesta/indexacion/retrieval, ChromaDB como vector
store por defecto, con Qdrant como ruta de escalado futura).

Modelo de embeddings por defecto: uno pequeno y multilingue de
sentence-transformers, ejecutable en CPU sin necesidad de GPU ni de una
API externa de pago (a diferencia del parser VDU, un modelo de embeddings
de ~100-500MB es perfectamente viable en el portatil actual). Si mas
adelante se prefiere un embedding vía API (OpenAI, Voyage...), basta con
inyectar otro `embed_model` compatible con LlamaIndex -- ver `build_index`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"
DEFAULT_COLLECTION_NAME = "bastanteo_chunks"


def _default_embed_model():
    """Carga perezosa del modelo de embeddings por defecto (evita descargar
    el modelo -~470MB- solo por importar este modulo; solo se descarga la
    primera vez que se llama a build_index sin pasar embed_model)."""
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    return HuggingFaceEmbedding(model_name=DEFAULT_EMBED_MODEL_NAME)


def build_nodes(chunks: list[dict[str, Any]]):
    """Convierte chunks (ver rag/chunking.py) en TextNode de LlamaIndex."""
    from llama_index.core.schema import TextNode

    nodes = []
    for chunk in chunks:
        nodes.append(
            TextNode(
                id_=chunk["chunk_id"],
                text=chunk["text"],
                metadata=chunk["metadata"],
            )
        )
    return nodes


def build_index(
    nodes: list[Any],
    persist_dir: str | Path = "03_data/generated/chroma",
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embed_model: Any = None,
):
    """Crea (o reabre) una coleccion ChromaDB persistente en `persist_dir`
    e indexa `nodes` con LlamaIndex.

    `embed_model=None` usa el modelo por defecto (ver _default_embed_model).
    En los tests se inyecta `llama_index.core.embeddings.MockEmbedding` para
    no depender de red ni de un modelo real (ver tests/rag/test_index_store.py).
    """
    import chromadb
    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.vector_stores.chroma import ChromaVectorStore

    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(collection_name)

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    return VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model or _default_embed_model(),
    )


def query(index: Any, question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Recupera los `top_k` chunks mas relevantes para `question` y los
    devuelve como citas trazables (documento, pagina, bloques, bbox) en vez
    de como texto plano -- esto es lo que alimentara `bastanteo_evidence`
    en el agente (04_src/agent/)."""
    retriever = index.as_retriever(similarity_top_k=top_k)
    results = retriever.retrieve(question)

    citations = []
    for result in results:
        node = result.node
        citations.append(
            {
                "chunk_id": node.node_id,
                "score": result.score,
                "text": node.get_content(),
                "document_id": node.metadata.get("document_id"),
                "page_number": node.metadata.get("page_number"),
                "section": node.metadata.get("section"),
                "block_ids": node.metadata.get("block_ids"),
                "bbox": node.metadata.get("bbox"),
            }
        )
    return citations

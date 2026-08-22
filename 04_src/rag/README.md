# 04_src/rag

Responsabilidad: chunking layout-aware, embeddings, persistencia en vector store (ChromaDB por defecto) y retrieval con filtros y scoring.

No debe: implementar lógica de agente conversacional compleja (eso vive en `04_src/agent/`, que consume `query()` como herramienta).

Los chunks preservan metadatos (documento, página, sección, tipo de bloque, bbox envolvente) — no solo texto plano — para que el resultado sea trazable (hipótesis H2/H3 del TFM: RAG layout-aware vs. texto plano).

## Piezas

- `chunking.py` — `build_chunks(document, case_id, max_chars=1000)`: agrupa bloques de un documento (esquema v1.1, salida de `normalizer/`) respetando secciones; nunca parte un bloque. Los `title`/`section_header` se guardan como encabezado del siguiente chunk en vez de ser un chunk vacío.
- `index_store.py` — `build_nodes()`, `build_index()`, `query()`: envuelve LlamaIndex + ChromaDB. Embedding por defecto: `intfloat/multilingual-e5-small` (CPU, sin API de pago — a diferencia del parser VDU, un modelo de embeddings de este tamaño sí es viable en el portátil actual).

## Uso

```python
from normalizer import build_document_entry
from rag import build_chunks, build_nodes, build_index, query

doc = build_document_entry(parser_result, document_id="DOC-0001", document_type_pred="solicitud")
chunks = build_chunks(doc, case_id="EXP-2026-0001")
nodes = build_nodes(chunks)
index = build_index(nodes)  # persiste en 03_data/generated/chroma/ por defecto

citas = query(index, "¿Consta el DNI del solicitante?", top_k=3)
# cada cita trae: chunk_id, score, text, document_id, page_number, section, block_ids, bbox
```

## Tests

```bash
pytest tests/rag/ -v
```

`test_chunking.py` no tiene dependencias externas. `test_index_store.py` usa `MockEmbedding` de LlamaIndex y un cliente Chroma en memoria (`EphemeralClient`), para no descargar el modelo real de embeddings ni escribir en disco durante los tests.

## Nota de coste/tiempo

La primera vez que se ejecute `build_index()` sin pasar `embed_model`, se descargará `intfloat/multilingual-e5-small` (~470MB) desde Hugging Face. Las siguientes ejecuciones lo reutilizan desde caché local.

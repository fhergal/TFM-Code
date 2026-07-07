# 04_src/rag

Responsabilidad: chunking layout-aware, embeddings, persistencia en vector store (ChromaDB por defecto) y retrieval con filtros y scoring.

No debe: implementar lógica de agente conversacional compleja.

Los chunks deben preservar metadatos: documento, página, tipo de bloque, sección y bbox — no solo texto plano — para que el resultado sea trazable (requisito H2/H3 del TFM).

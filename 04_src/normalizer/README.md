# 04_src/normalizer

Responsabilidad: convertir la salida nativa del parser al esquema canónico `CanonicalDocumentParse v1.1` (`../../specs/canonical-document-parse-v1.1.md` / `canonical_document_parse.schema.json`), validar estructura y tipos, y añadir metadatos mínimos obligatorios.

No debe: llamar al LLM ni acoplarse a la UI.

Nota: usar el esquema v1.1 unificado como formato de salida, no el borrador plano (`doc_id/page/block_id/type/...`) descrito en el hilo de decisiones de implementación — ese borrador quedó fusionado dentro de v1.1 (ver tabla de mapeo en el spec).

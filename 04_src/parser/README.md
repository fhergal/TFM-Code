# 04_src/parser

Responsabilidad: ejecutar el parsing sobre imagen/PDF con el modelo VDU (Chandra OCR-2 por defecto) y devolver la salida nativa + metadatos de ejecución.

No debe: decidir chunking ni indexar en el vector store (eso vive en `rag/`).

Contrato de salida esperado: ver `../../specs/canonical-document-parse-v1.1.md` (el parser produce la entrada cruda que `normalizer/` transforma al esquema canónico).

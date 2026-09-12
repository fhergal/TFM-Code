# 04_src/ui

Demo mínima en Gradio: carga de documento -> parseo -> normalización -> indexación -> pregunta/respuesta y bastanteo automático, mostrando evidencias trazables (documento fuente, página, bloque).

No debe: contener lógica core de parsing, retrieval o juicio (eso vive en `parser/`, `normalizer/`, `rag/` y `agent/`; este módulo solo orquesta y cablea Gradio).

## Piezas

- `pipeline.py` — orquestación pura (sin importar `gradio`), para poder testearla sin esa dependencia: `process_document()`, `build_index_for_case()`, `ask_question()`, `run_bastanteo_over_case()`.
- `naive_retriever.py` — retriever de respaldo por solapamiento de palabras (sin embeddings ni vector store), usado en el **modo demo**.
- `sample_case.json` — expediente de ejemplo, válido contra el esquema v1.1, para el modo demo.
- `app.py` — cableado de componentes Gradio contra `pipeline.py`. Ejecutar con `python 04_src/ui/app.py`.

## Dos modos

1. **Modo real**: sube un documento, se parsea con Datalab (`DATALAB_API_KEY` requerido) y se indexa con ChromaDB/LlamaIndex reales.
2. **Modo demo**: botón "Cargar expediente de ejemplo" — usa `sample_case.json` + `naive_retriever`, sin API key ni dependencias pesadas. Corre el mismo agente de bastanteo (`agent/`) que el modo real, solo cambia el retriever.

En ambos modos, "Bastanteo automático" ejecuta el catálogo de ejemplo de `agent/catalog.py` (placeholder hasta tener el mapa documental real — ver tarea pendiente #8).

## Tests

```bash
pytest tests/ui/ -v
```

Los tests cubren `pipeline.py` y `naive_retriever.py` sin necesidad de tener `gradio` instalado (ver nota en `tests/ui/test_pipeline.py`).

### Test omitido (1 skipped — esperado)

`test_build_index_for_case_raises_pipeline_error_if_deps_missing` (en `tests/ui/test_pipeline.py`) se **salta cuando `llama-index`/`chromadb` están instalados**, que es el caso en cualquier máquina con el entorno completo. Solo verifica el camino de error "dependencias ausentes"; la integración real con ChromaDB se prueba en `tests/rag/test_index_store.py`. Por tanto, `1 skipped` es el resultado correcto y no indica un fallo.

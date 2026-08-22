"""Orquestación de punta a punta para la demo (ver README.md): parser ->
normalizador -> indice RAG -> pregunta/respuesta o bastanteo vía agente.

Deliberadamente separado de `app.py` (que solo debe contener el cableado de
componentes Gradio) para poder testear la logica de orquestacion sin
importar gradio ni sus dependencias -- ver tests/ui/test_pipeline.py.

Dos modos de uso, mismo codigo de agente por debajo:

- Modo real: `process_document()` + `build_index()` usan el parser Datalab
  real y el índice ChromaDB/LlamaIndex real (requieren DATALAB_API_KEY y
  las dependencias pesadas instaladas).
- Modo demo: `load_demo_case()` + `naive_retriever.build_naive_retriever()`
  no requieren ninguna API key ni dependencia pesada -- útiles para
  presentar el flujo cuando el entorno no tiene todo instalado (ver aviso
  en rag/README.md sobre el tamaño de las dependencias).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from agent import Requirement, run_bastanteo
from agent.catalog import EXAMPLE_REQUIREMENTS
from normalizer import build_case_envelope, build_document_entry

from .naive_retriever import build_naive_retriever

_SAMPLE_CASE_PATH = Path(__file__).resolve().parent / "sample_case.json"

RetrieveFn = Callable[[str, int], list[dict[str, Any]]]


class PipelineError(RuntimeError):
    """Error de orquestación con un mensaje pensado para mostrarse tal cual
    en la UI (no una traza técnica)."""


def load_demo_case() -> dict[str, Any]:
    """Carga el expediente de ejemplo embebido (sample_case.json), ya
    válido contra el esquema v1.1, para el modo demo sin API key."""
    return json.loads(_SAMPLE_CASE_PATH.read_text(encoding="utf-8"))


def process_document(
    file_path: str,
    case_id: str,
    procedure_type: str = "prestacion_inss",
    parser_backend: str = "datalab",
) -> dict[str, Any]:
    """Parsea un documento real y devuelve el `case` (esquema v1.1) con un
    único documento en `document_inventory`. Lanza `PipelineError` con un
    mensaje entendible si falta la API key o el fichero no existe."""
    from parser import get_parser

    try:
        p = get_parser(parser_backend)
    except (RuntimeError, ValueError, ImportError) as exc:
        # ImportError: falta el SDK del backend (p. ej. datalab-python-sdk).
        # RuntimeError: falta la API key. ValueError: backend desconocido.
        raise PipelineError(str(exc)) from exc

    try:
        raw = p.parse(file_path, output_format="json")
    except FileNotFoundError as exc:
        raise PipelineError(f"No se encontró el fichero: {file_path}") from exc

    document_id = "DOC-0001"
    doc_entry = build_document_entry(raw, document_id=document_id)
    case = build_case_envelope(
        case_id=case_id,
        procedure_type=procedure_type,
        documents=[doc_entry],
        parser_result=raw,
    )
    return case


def build_index_for_case(case: dict[str, Any]):
    """Construye un índice RAG real (ChromaDB en memoria) a partir de un
    `case`. Lanza `PipelineError` si faltan las dependencias pesadas."""
    from rag import build_chunks, build_index, build_nodes

    try:
        chunks = []
        for document in case.get("document_inventory", []):
            chunks.extend(build_chunks(document, case_id=case.get("case_id")))
        nodes = build_nodes(chunks)
        return build_index(nodes)
    except ModuleNotFoundError as exc:
        raise PipelineError(
            "Faltan dependencias de RAG (llama-index / chromadb). "
            "Instala con `pip install -e \".[dev]\"` o usa el modo demo."
        ) from exc


def make_retrieve_fn_from_index(index) -> RetrieveFn:
    from rag import query as rag_query

    return lambda q, k: rag_query(index, q, top_k=k)


def ask_question(retrieve_fn: RetrieveFn, question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Devuelve las citas trazables (documento/pagina/bloque) mas relevantes
    para `question`, sin pasar por el agente -- pregunta libre."""
    return retrieve_fn(question, top_k)


def run_bastanteo_over_case(
    retrieve_fn: RetrieveFn,
    requirements: list[Requirement] | None = None,
) -> dict[str, Any]:
    """Ejecuta el agente de bastanteo (catalogo de ejemplo por defecto,
    ver agent/catalog.py) sobre el `retrieve_fn` dado (real o naive)."""
    return run_bastanteo(requirements or EXAMPLE_REQUIREMENTS, retrieve_fn)


def demo_retrieve_fn() -> RetrieveFn:
    """Atajo: retriever naive sobre el expediente de ejemplo, listo para
    usar en el modo demo sin ninguna dependencia pesada."""
    return build_naive_retriever(load_demo_case())

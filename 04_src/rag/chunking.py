"""Chunking LAYOUT-AWARE: agrupa bloques de un documento (esquema v1.1) en
chunks para indexar, respetando secciones y límites de bloque -- nunca
se parte un bloque por la mitad, a diferencia de un chunking por longitud
de texto plano (ver Hilo 01, "Innovación 2: chunking layout-aware").

Regla de agrupación (deliberadamente simple para este PoC):
    - Recorre los bloques de cada página en orden de lectura.
    - Mientras el bloque siguiente pertenezca a la misma `semantics.section`
      Y el chunk no supere `max_chars`, se añade al grupo actual.
    - Si cambia la sección, o se supera el presupuesto de caracteres,
      se cierra el chunk actual y se abre uno nuevo.
    - Los bloques `title`/`section_header` se guardan como encabezado del
      chunk (se anteponen al texto) en vez de generar un chunk propio sin
      contenido recuperable.
"""

from __future__ import annotations

from typing import Any

_HEADER_TYPES = {"title", "section_header"}

_NO_SECTION = "__sin_seccion__"


def _envelope_bbox(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rectángulo envolvente de los bbox de todos los bloques del chunk,
    para poder resaltar/localizar el chunk completo en la página."""
    boxes = [b["bbox"] for b in blocks if b.get("bbox")]
    if not boxes:
        return None
    unit = boxes[0].get("unit", "pixel")
    return {
        "x0": min(b["x0"] for b in boxes),
        "y0": min(b["y0"] for b in boxes),
        "x1": max(b["x1"] for b in boxes),
        "y1": max(b["y1"] for b in boxes),
        "unit": unit,
    }


def _finalize_chunk(
    document_id: str,
    case_id: str | None,
    page_number: int,
    section: str | None,
    header_texts: list[str],
    blocks: list[dict[str, Any]],
    chunk_index: int,
) -> dict[str, Any]:
    body = "\n".join(b.get("text", "") for b in blocks if b.get("text"))
    text = "\n".join([*header_texts, body]) if header_texts else body

    return {
        "chunk_id": f"{document_id}-P{page_number:02d}-C{chunk_index:03d}",
        "text": text,
        "metadata": {
            "case_id": case_id,
            "document_id": document_id,
            "page_number": page_number,
            "section": None if section == _NO_SECTION else section,
            "block_ids": [b["block_id"] for b in blocks],
            "block_types": sorted({b["block_type"] for b in blocks}),
            "bbox": _envelope_bbox(blocks),
        },
    }


def build_chunks(document: dict[str, Any], case_id: str | None = None, max_chars: int = 1000) -> list[dict[str, Any]]:
    """Construye chunks layout-aware a partir de UN documento (esquema v1.1,
    ver build_document_entry en 04_src/normalizer/).

    Devuelve una lista de dicts `{chunk_id, text, metadata}` listos para
    convertirse en nodos de LlamaIndex (ver index_store.build_nodes).
    """
    document_id = document["document_id"]
    chunks: list[dict[str, Any]] = []

    for page in document.get("pages", []):
        page_number = page["page_number"]
        current_blocks: list[dict[str, Any]] = []
        current_headers: list[str] = []
        current_section = _NO_SECTION
        current_len = 0
        chunk_index = 0

        def flush() -> None:
            nonlocal current_blocks, current_headers, current_len, chunk_index
            if current_blocks:
                chunk_index += 1
                chunks.append(
                    _finalize_chunk(
                        document_id, case_id, page_number, current_section,
                        current_headers, current_blocks, chunk_index,
                    )
                )
            current_blocks = []
            current_headers = []
            current_len = 0

        for block in page.get("blocks", []):
            if block["block_type"] in _HEADER_TYPES:
                # Un header cierra el chunk anterior y se guarda como
                # encabezado del siguiente (da contexto sin ser, por si
                # solo, un chunk recuperable vacio de contenido).
                flush()
                current_headers.append(block.get("text", ""))
                continue

            section = (block.get("semantics") or {}).get("section")
            normalized_section = section if section is not None else _NO_SECTION
            block_text_len = len(block.get("text", ""))

            section_changed = normalized_section != current_section and current_blocks
            budget_exceeded = current_len + block_text_len > max_chars and current_blocks

            if section_changed or budget_exceeded:
                flush()

            current_section = normalized_section
            current_blocks.append(block)
            current_len += block_text_len

        flush()

    return chunks

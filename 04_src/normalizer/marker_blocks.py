"""Aplana el arbol de bloques que devuelve la API de Datalab (basada en
Marker/Chandra) al formato de bloques planos de CanonicalDocumentParse v1.1.

*** AVISO IMPORTANTE (léelo antes de confiar en este modulo) ***
Datalab NO publica en su OpenAPI el esquema interno del campo `json` de
`/convert` (lo tipan como "object" generico). Lo que hay aqui abajo es mi
mejor estimacion, basada en el esquema de bloques publico del proyecto
Marker de Datalab (arbol Document -> Page -> bloques con `block_type`,
`children`, `bbox`/`polygon`, `html`). Puede haber cambiado de nombre de
campo entre versiones.

Antes de usar esto contra datos reales para el TFM:
  1. Ejecuta `python 04_src/parser/run_parser.py <doc> --format json` con tu
     DATALAB_API_KEY real.
  2. Abre el JSON guardado en 03_data/generated/parsed/ y compara con los
     nombres de campo asumidos aqui (BLOCK_TYPE_MAP, _get_bbox, _get_text).
  3. Ajusta lo que no coincida. Los tests de este modulo usan un arbol
     SINTETICO con esta forma asumida, no una respuesta real -- por eso no
     bastan para validar el mapeo contra la API real.
"""

from __future__ import annotations

import html as html_module
import re
from typing import Any

# Mapeo de block_type de Marker/Datalab -> block_type de CanonicalDocumentParse v1.1
# (ver Anexo B / specs/canonical-document-parse-v1.1.md, seccion 4).
# Tipos no listados aqui caen en "free_note" (ver _map_block_type) en vez de
# fallar, porque el listado real de tipos de Marker es mas largo (Equation,
# Code, Reference, TableOfContents, Caption, etc.) y preferimos degradar con
# aviso a romper el pipeline por un tipo no previsto.
BLOCK_TYPE_MAP: dict[str, str] = {
    "Title": "title",
    "SectionHeader": "section_header",
    "Text": "paragraph",
    "TextInlineMath": "paragraph",
    "Form": "form_field",
    "FieldName": "key_value",
    "FieldValue": "key_value",
    "Table": "table",
    "TableRow": "table_row",
    "TableCell": "table_cell",
    "Checkbox": "checkbox",
    "Handwriting": "paragraph",
    "Signature": "signature",
    "Stamp": "stamp",
    "Picture": "image_region",
    "Figure": "image_region",
    "PageHeader": "header",
    "PageFooter": "footer",
    "Footnote": "free_note",
    "Line": "paragraph",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _map_block_type(marker_type: str) -> str:
    return BLOCK_TYPE_MAP.get(marker_type, "free_note")


def _html_to_text(fragment: str) -> str:
    """Extraccion de texto muy simple (sin dependencias): quita tags HTML y
    des-escapa entidades. Suficiente para un bloque de texto corto; si el
    bloque es una tabla compleja, conviene tratarla aparte (TODO futuro)."""
    return html_module.unescape(_TAG_RE.sub("", fragment)).strip()


def _get_text(node: dict[str, Any]) -> str:
    if "text" in node and isinstance(node["text"], str):
        return node["text"].strip()
    if "html" in node and isinstance(node["html"], str):
        return _html_to_text(node["html"])
    return ""


def _get_bbox(node: dict[str, Any]) -> dict[str, Any] | None:
    """Devuelve {x0,y0,x1,y1,unit}. Prioriza `bbox` explicito; si solo hay
    `polygon` (lista de puntos [x,y]), calcula el rectangulo envolvente."""
    bbox = node.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        x0, y0, x1, y1 = bbox
        return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "unit": "pixel"}

    polygon = node.get("polygon")
    if isinstance(polygon, (list, tuple)) and polygon:
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys), "unit": "pixel"}

    return None


def flatten_marker_tree(raw_json: dict[str, Any], document_id: str) -> list[dict[str, Any]]:
    """Recorre el arbol Document -> Page -> bloques y devuelve una lista
    PLANA de bloques v1.1, cada uno con su `page_anchor.page_number`
    (1-indexado) para que el llamador (normalizer/__init__.py) los agrupe
    por pagina al construir `pages[]`.
    """
    blocks: list[dict[str, Any]] = []
    reading_order = 0

    def walk(node: dict[str, Any], page_number: int) -> None:
        nonlocal reading_order
        node_type = node.get("block_type", "Unknown")

        if node_type == "Page":
            page_number = node.get("page_number", page_number)

        children = node.get("children") or []

        # Consideramos "hoja de contenido" cualquier bloque que no sea
        # Document/Page y que tenga texto o bbox propio; si tiene hijos con
        # contenido, los procesamos tambien (algunos bloques, como Table,
        # tienen tanto contenido propio como celdas hijas).
        if node_type not in ("Document", "Page"):
            text = _get_text(node)
            bbox = _get_bbox(node)
            # bbox es un campo obligatorio en el esquema v1.1 (es la base del
            # "RAG layout-aware"): si un nodo no trae bbox ni polygon, no
            # podemos emitirlo como bloque valido, asi que se descarta aqui
            # en vez de dejar que falle mas tarde la validacion del schema.
            if bbox is not None:
                reading_order += 1
                blocks.append(
                    {
                        "block_id": node.get("id") or f"{document_id}-P{page_number:02d}-B{reading_order:03d}",
                        "block_type": _map_block_type(node_type),
                        "label": None,
                        "text": text,
                        "normalized_text": text,
                        "bbox": bbox,
                        "reading_order": reading_order,
                        "semantics": {
                            "entity_type": None,
                            "section": None,
                            "required_for_bastanteo": None,
                        },
                        "quality": {
                            "confidence": node.get("confidence"),
                            "ocr_noise_level": None,
                            "handwritten": node_type == "Handwriting",
                            "crossed_out": None,
                        },
                        "_page_number": page_number,  # se usa y se descarta al agrupar por pagina
                    }
                )

        for child in children:
            walk(child, page_number)

    walk(raw_json, page_number=1)
    return blocks

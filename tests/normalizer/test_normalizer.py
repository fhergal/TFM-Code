"""Tests del normalizer (parser nativo -> CanonicalDocumentParse v1.1).

IMPORTANTE: el arbol `SAMPLE_MARKER_TREE` de abajo es SINTETICO, construido
a partir de mi mejor entendimiento del esquema publico de bloques de Marker
(Document -> Page -> bloques con block_type/bbox|polygon/html/children).
Datalab no publica el esquema exacto de su campo `json` en el OpenAPI (solo
dice "object"). Estos tests validan que NUESTRO codigo de mapeo hace lo que
promete con esa forma asumida -- NO son una garantia de que la respuesta
real de la API tenga exactamente esta forma. Ver el aviso en
04_src/normalizer/marker_blocks.py antes de confiar en esto con datos reales.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from normalizer import build_case_envelope, build_document_entry, validate
from normalizer.marker_blocks import flatten_marker_tree

SAMPLE_MARKER_TREE = {
    "block_type": "Document",
    "children": [
        {
            "block_type": "Page",
            "page_number": 1,
            "children": [
                {
                    "id": "b1",
                    "block_type": "SectionHeader",
                    "html": "<h1>Solicitud de prestaci&oacute;n</h1>",
                    "bbox": [10, 10, 200, 40],
                },
                {
                    "id": "b2",
                    "block_type": "Text",
                    "html": "<p>DNI: 12345678Z</p>",
                    "polygon": [[10, 50], [300, 50], [300, 80], [10, 80]],
                },
                {
                    "id": "b3",
                    "block_type": "Table",
                    "bbox": [10, 90, 300, 200],
                    "children": [
                        {
                            "id": "b3-1",
                            "block_type": "TableCell",
                            "html": "<td>Campo</td>",
                            "bbox": [10, 90, 150, 110],
                        }
                    ],
                },
                {
                    # Nodo sin bbox ni polygon: debe descartarse (ver comentario
                    # en marker_blocks.flatten_marker_tree).
                    "id": "b4",
                    "block_type": "Text",
                    "html": "<p>sin coordenadas</p>",
                },
            ],
        }
    ],
}


def test_flatten_marker_tree_maps_types_text_and_bbox():
    blocks = flatten_marker_tree(SAMPLE_MARKER_TREE, document_id="DOC-0001")

    # b4 (sin bbox/polygon) se descarta -> quedan 4 bloques (b1, b2, b3, b3-1)
    assert len(blocks) == 4

    header, text, table, cell = blocks

    assert header["block_type"] == "section_header"
    assert header["text"] == "Solicitud de prestación"
    assert header["bbox"] == {"x0": 10, "y0": 10, "x1": 200, "y1": 40, "unit": "pixel"}

    assert text["block_type"] == "paragraph"
    assert text["text"] == "DNI: 12345678Z"
    # bbox derivado de polygon (envolvente min/max)
    assert text["bbox"] == {"x0": 10, "y0": 50, "x1": 300, "y1": 80, "unit": "pixel"}

    assert table["block_type"] == "table"
    assert cell["block_type"] == "table_cell"

    # reading_order es creciente y unico
    orders = [b["reading_order"] for b in blocks]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)


def test_unmapped_block_type_falls_back_to_free_note():
    tree = {
        "block_type": "Document",
        "children": [
            {
                "block_type": "Page",
                "page_number": 1,
                "children": [
                    {"id": "x1", "block_type": "TipoRarisimoNoPrevisto", "html": "<p>?</p>", "bbox": [0, 0, 1, 1]}
                ],
            }
        ],
    }
    blocks = flatten_marker_tree(tree, document_id="DOC-X")
    assert blocks[0]["block_type"] == "free_note"


def _fake_parser_result(raw=SAMPLE_MARKER_TREE):
    return SimpleNamespace(
        raw=raw,
        source_path=Path("solicitud_01.pdf"),
        backend="datalab",
        model_name="datalab-managed-convert(mode=balanced)",
        output_format="json",
        page_count=1,
        quality_score=4.1,
        elapsed_seconds=1.23,
        extra_metadata={},
    )


def test_build_document_entry_groups_blocks_by_page():
    doc = build_document_entry(
        _fake_parser_result(), document_id="DOC-0001", document_type_pred="solicitud"
    )

    assert doc["document_id"] == "DOC-0001"
    assert doc["document_type_pred"] == "solicitud"
    assert len(doc["pages"]) == 1
    assert doc["pages"][0]["page_number"] == 1
    assert len(doc["pages"][0]["blocks"]) == 4
    # los campos desconocidos (document_type_gold, origin.mime_type, etc.)
    # se omiten en vez de aparecer como null
    assert "document_type_gold" not in doc
    assert "mime_type" not in doc["origin"]


def test_full_case_envelope_validates_against_json_schema():
    doc = build_document_entry(
        _fake_parser_result(), document_id="DOC-0001", document_type_pred="solicitud"
    )
    case = build_case_envelope(
        case_id="EXP-2026-0001",
        procedure_type="prestacion_inss",
        documents=[doc],
        parser_result=_fake_parser_result(),
    )

    validate(case, part="case")  # no debe lanzar


def test_case_without_document_type_pred_fails_schema_validation():
    """document_type_pred es obligatorio en el esquema v1.1: si no se ha
    corrido todavia un clasificador, el caso NO debe validar como completo.
    Este test documenta ese comportamiento esperado (no es un bug)."""
    import jsonschema

    doc = build_document_entry(_fake_parser_result(), document_id="DOC-0001")
    case = build_case_envelope(
        case_id="EXP-2026-0001",
        procedure_type="prestacion_inss",
        documents=[doc],
        parser_result=_fake_parser_result(),
    )

    with pytest.raises(jsonschema.exceptions.ValidationError):
        validate(case, part="case")

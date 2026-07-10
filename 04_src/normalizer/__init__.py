"""
Modulo normalizer: convierte la salida NATIVA de un backend de parser
(`parser.base.ParserResult`) al esquema canonico CanonicalDocumentParse v1.1
(ver ../../specs/canonical-document-parse-v1.1.md).

No debe (ver README.md de este modulo):
    - llamar al LLM,
    - acoplarse a la UI.

Uso tipico:

    from parser import get_parser
    from normalizer import build_document_entry, build_case_envelope, validate

    p = get_parser("datalab")
    raw = p.parse("solicitud_01.pdf", output_format="json")

    doc = build_document_entry(raw, document_id="DOC-0001")
    case = build_case_envelope(
        case_id="EXP-2026-0001",
        procedure_type="prestacion_inss",
        documents=[doc],
        parser_result=raw,
    )
    validate(case, part="case")  # lanza si no cumple el JSON Schema v1.1
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .marker_blocks import flatten_marker_tree

# parser.base.ParserResult -- import perezoso/opcional para no forzar la
# dependencia de "parser" si alguien solo quiere usar el normalizer con un
# dict ya en mano (por ejemplo, en tests).
try:
    from parser.base import ParserResult
except ImportError:  # pragma: no cover
    ParserResult = None  # type: ignore[assignment, misc]

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "specs" / "canonical_document_parse.schema.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact(obj: Any) -> Any:
    """Elimina recursivamente las claves cuyo valor es None.

    Necesario porque el JSON Schema v1.1 declara los campos opcionales con
    tipos estrictos (string/object/etc.) SIN admitir null: si dejaramos
    `"document_date": None` en el dict, `json.dumps` lo convertiria en
    `null` y la validacion fallaria por tipo incorrecto. Mejor omitir del
    todo el campo cuando aun no se conoce su valor, en vez de mandarlo a null.
    """
    if isinstance(obj, dict):
        return {k: _compact(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_compact(v) for v in obj]
    return obj


def _group_blocks_by_page(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages: dict[int, list[dict[str, Any]]] = {}
    for block in blocks:
        page_number = block.pop("_page_number", 1)
        pages.setdefault(page_number, []).append(block)

    return [
        {"page_number": page_number, "page_size": None, "blocks": pages[page_number]}
        for page_number in sorted(pages)
    ]


def build_document_entry(
    parser_result: Any,
    document_id: str,
    document_type_pred: str | None = None,
    document_type_gold: str | None = None,
    document_metadata: dict[str, Any] | None = None,
    input_channel: str | None = None,
) -> dict[str, Any]:
    """Construye UN elemento de `document_inventory[]` (esquema v1.1) a partir
    de un `ParserResult` (salida nativa del parser, formato "json" de Datalab).

    Nota: `extracted_fields` se deja vacio aqui a proposito -- la extraccion
    de campos clave (DNI, NUSS, fecha...) a partir de bloques semanticos es
    el siguiente paso logico (podria vivir en este mismo modulo o en
    04_src/agent/, segun se decida), no se resuelve en este primer PoC.
    """
    raw = parser_result.raw if hasattr(parser_result, "raw") else parser_result
    if not isinstance(raw, dict):
        raise ValueError(
            "build_document_entry espera ParserResult.raw como dict (output_format='json'). "
            f"Se recibio: {type(raw)!r}"
        )

    blocks = flatten_marker_tree(raw, document_id=document_id)
    pages = _group_blocks_by_page(blocks)

    source_path = getattr(parser_result, "source_path", None)
    page_count = getattr(parser_result, "page_count", None)

    entry = {
        "document_id": document_id,
        "document_type_pred": document_type_pred,
        "document_type_gold": document_type_gold,
        "origin": {
            "source_format": None,  # rellenar segun se conozca el origen real (scan/native_pdf/photo)
            "file_name": Path(source_path).name if source_path else None,
            "mime_type": None,
            "page_count": page_count,
            "input_channel": input_channel,
        },
        "document_metadata": document_metadata
        or {
            "issuer_org": None,
            "document_date": None,
            "language": None,
            "signature_status": None,
            "legibility_level": None,
            "template_version": None,
        },
        "pages": pages,
        "extracted_fields": [],
    }
    return _compact(entry)


def build_case_envelope(
    case_id: str,
    procedure_type: str,
    documents: list[dict[str, Any]],
    parser_result: Any,
    source_batch_id: str | None = None,
) -> dict[str, Any]:
    """Envuelve una o mas entradas de documento (build_document_entry) en el
    objeto de nivel "expediente" del esquema v1.1."""
    model_name = getattr(parser_result, "model_name", "unknown")

    envelope = {
        "schema_version": "1.1",
        "case_id": case_id,
        "procedure_type": procedure_type,
        "source_batch_id": source_batch_id,
        "created_at": _now_iso(),
        "parser": {
            "canonical_parser": model_name,
            "parser_family": "vlm_ocr_free",
            "model_version": None,
            "raw_output_format": getattr(parser_result, "output_format", "json"),
            "confidence_global": getattr(parser_result, "quality_score", None),
        },
        "case_context": {
            "domain": "bastanteo_administrativo",
            "language_expected": ["es"],
            "country": "ES",
        },
        "expected_document_map": [],
        "document_inventory": documents,
        "bastanteo_evidence": [],
        "bastanteo_gold": None,
    }
    return _compact(envelope)


def validate(payload: dict[str, Any], part: str = "case") -> None:
    """Valida `payload` contra specs/canonical_document_parse.schema.json.

    Args:
        part: "case" valida contra el esquema raiz completo; "document"
            valida contra la sub-definicion #/definitions/document.
    Lanza jsonschema.exceptions.ValidationError si no cumple.
    """
    import jsonschema

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

    if part == "case":
        jsonschema.validate(instance=payload, schema=schema)
    elif part == "document":
        doc_schema = {**schema["definitions"]["document"], "definitions": schema["definitions"]}
        jsonschema.validate(instance=payload, schema=doc_schema)
    else:
        raise ValueError("part debe ser 'case' o 'document'")


__all__ = ["build_document_entry", "build_case_envelope", "validate", "flatten_marker_tree"]

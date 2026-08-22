"""Verifica que la salida real de `run_bastanteo` (bastanteo_evidence +
bastanteo_gold) encaja en el `case` completo del esquema v1.1 -- es decir,
que agent + normalizer + JSON Schema son compatibles de punta a punta, no
solo por separado."""

from __future__ import annotations

from agent import Requirement, RuleBasedJudge, run_bastanteo
from normalizer import validate

MINIMAL_DOCUMENT = {
    "document_id": "DOC-0001",
    "document_type_pred": "solicitud",
    "origin": {"source_format": "scan", "page_count": 1},
    "document_metadata": {"language": "es"},
    "pages": [
        {
            "page_number": 1,
            "blocks": [
                {
                    "block_id": "DOC-0001-P01-B001",
                    "block_type": "form_field",
                    "text": "12345678Z",
                    "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10, "unit": "pixel"},
                }
            ],
        }
    ],
}


def _retrieve_fn(query, top_k):
    return [
        {
            "document_id": "DOC-0001",
            "page_number": 1,
            "score": 0.9,
            "text": "DNI: 12345678Z",
            "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10, "unit": "pixel"},
            "block_ids": ["DOC-0001-P01-B001"],
        }
    ]


def test_bastanteo_output_merged_into_case_validates_against_schema():
    requirements = [Requirement("REQ-DNI", "Consta DNI del solicitante", "Cual es el DNI?")]
    bastanteo = run_bastanteo(requirements, _retrieve_fn, judge=RuleBasedJudge(min_score=0.5))

    case = {
        "schema_version": "1.1",
        "case_id": "EXP-2026-0001",
        "procedure_type": "prestacion_inss",
        "document_inventory": [MINIMAL_DOCUMENT],
        "bastanteo_evidence": bastanteo["bastanteo_evidence"],
        "bastanteo_gold": bastanteo["bastanteo_gold"],
    }

    validate(case, part="case")  # no debe lanzar

    assert case["bastanteo_gold"]["status"] == "VALIDO"


def test_bastanteo_output_with_missing_requirement_still_validates():
    requirements = [Requirement("REQ-ANEXO", "Consta anexo", "Hay anexo?")]
    bastanteo = run_bastanteo(requirements, lambda q, k: [])

    case = {
        "schema_version": "1.1",
        "case_id": "EXP-2026-0002",
        "procedure_type": "prestacion_inss",
        "document_inventory": [MINIMAL_DOCUMENT],
        "bastanteo_evidence": bastanteo["bastanteo_evidence"],
        "bastanteo_gold": bastanteo["bastanteo_gold"],
    }

    validate(case, part="case")  # el evidence con linked_document_id="" debe seguir validando

    assert case["bastanteo_gold"]["status"] == "INCOMPLETO"

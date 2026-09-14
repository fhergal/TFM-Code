"""Tests del evaluador Fase 3 semantico (03_data/generators/evaluar_fase3_semantico.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "03_data" / "generators"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "04_src"))

import json

import pytest

from evaluar_fase3_semantico import build_case_index, evaluate_case, load_manifest, run_evaluation, select_subset


def _manifest():
    return [
        {"case_id": "EXP-A", "status_gold": "VALIDO", "file": "a.json"},
        {"case_id": "EXP-B", "status_gold": "VALIDO", "file": "b.json"},
        {"case_id": "EXP-C", "status_gold": "INCOMPLETO", "file": "c.json"},
        {"case_id": "EXP-D", "status_gold": "RECHAZADO", "file": "d.json"},
    ]


def test_select_subset_balances_by_status_and_respects_limit():
    subset = select_subset(_manifest(), n_per_status=1)

    statuses = [c["status_gold"] for c in subset]
    assert statuses == ["VALIDO", "INCOMPLETO", "RECHAZADO"]


@pytest.fixture
def mock_embed_model():
    from llama_index.core.embeddings import MockEmbedding

    return MockEmbedding(embed_dim=8)


def _fake_case():
    return {
        "case_id": "EXP-TEST-0001",
        "document_inventory": [
            {
                "document_id": "DOC-0001",
                "document_type_gold": "ae_ciu_sol_prestacion",
                "pages": [
                    {
                        "page_number": 1,
                        "blocks": [
                            {
                                "block_id": "b1",
                                "block_type": "paragraph",
                                "text": "Consta la solicitud de prestacion (formulario C-157) cumplimentada.",
                                "bbox": {"x0": 0, "y0": 0, "x1": 100, "y1": 20, "unit": "pixel"},
                                "semantics": {"section": "solicitud"},
                            },
                        ],
                    }
                ],
            }
        ],
        "bastanteo_gold": {"status": "INCOMPLETO"},
    }


def test_build_case_index_returns_queryable_index(tmp_path, mock_embed_model):
    case = _fake_case()

    index = build_case_index(case, persist_dir=tmp_path / "chroma", embed_model=mock_embed_model)

    from rag.index_store import query

    results = query(index, "Consta la solicitud de prestacion?", top_k=3)
    assert len(results) > 0
    assert results[0]["document_id"] == "DOC-0001"


def test_evaluate_case_returns_expected_keys(tmp_path, mock_embed_model):
    case = _fake_case()
    case_meta = {"case_id": case["case_id"], "status_gold": "INCOMPLETO", "file": "irrelevant.json"}

    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "irrelevant.json").write_text(json.dumps(case), encoding="utf-8")

    result = evaluate_case(
        dataset_dir,
        case_meta,
        persist_dir=tmp_path / "chroma",
        embed_model=mock_embed_model,
        min_score=0.0,
    )

    for key in (
        "case_id", "status_real", "status_predicted", "status_match",
        "n_requisitos_documento", "n_requisitos_correctos", "requisito_accuracy",
        "latency_ms", "index_ms", "n_docs_expediente",
    ):
        assert key in result
    assert result["status_real"] == "INCOMPLETO"


def test_load_manifest_reads_manifest_json(tmp_path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "manifest.json").write_text(
        json.dumps([{"case_id": "EXP-A", "status_gold": "VALIDO", "file": "a.json"}]),
        encoding="utf-8",
    )

    manifest = load_manifest(dataset_dir)

    assert manifest == [{"case_id": "EXP-A", "status_gold": "VALIDO", "file": "a.json"}]


def test_run_evaluation_writes_aggregated_results(tmp_path, mock_embed_model):
    case = _fake_case()
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "manifest.json").write_text(
        json.dumps([{"case_id": case["case_id"], "status_gold": "INCOMPLETO", "file": "case.json"}]),
        encoding="utf-8",
    )
    (dataset_dir / "case.json").write_text(json.dumps(case), encoding="utf-8")

    out_path = tmp_path / "out.json"
    run_evaluation(
        dataset_dir=dataset_dir,
        n_per_status=1,
        min_score=0.0,
        out_path=out_path,
        embed_model=mock_embed_model,
    )

    output = json.loads(out_path.read_text(encoding="utf-8"))
    assert output["metadata"]["n_cases"] == 1
    assert "aggregated" in output
    assert output["individual_results"][0]["case_id"] == case["case_id"]

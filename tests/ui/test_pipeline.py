"""Tests de ui/pipeline.py -- deliberadamente NO importan `gradio` (que es
una dependencia pesada con su propio stack web) para poder verificar la
logica de orquestacion de forma rapida y aislada. `app.py` (el cableado de
componentes Gradio) no se testea aqui; ver README.md."""

from __future__ import annotations

import pytest

from ui import pipeline


def test_load_demo_case_is_valid_and_has_expected_document():
    case = pipeline.load_demo_case()

    assert case["case_id"] == "EXP-DEMO-0001"
    assert case["procedure_type"] == "aex_gestprestaciones_bada"
    # expediente BADA real: solicitud (C-157) + 5 documentos justificativos
    assert len(case["document_inventory"]) == 6
    assert case["document_inventory"][0]["document_id"] == "DOC-0001"


def test_demo_retrieve_fn_runs_full_agent_end_to_end():
    retrieve_fn = pipeline.demo_retrieve_fn()

    result = pipeline.run_bastanteo_over_case(retrieve_fn)

    assert "bastanteo_evidence" in result
    assert "bastanteo_gold" in result
    assert result["bastanteo_gold"]["status"] in ("VALIDO", "INCOMPLETO", "RECHAZADO")
    # el catalogo BADA (agent/catalog.py) deberia encontrar soporte para
    # todos los requisitos obligatorios en el expediente de ejemplo -> VALIDO
    assert result["bastanteo_gold"]["status"] == "VALIDO"
    assert len(result["bastanteo_evidence"]) == 8


def test_ask_question_returns_traceable_citations_in_demo_mode():
    retrieve_fn = pipeline.demo_retrieve_fn()

    citations = pipeline.ask_question(retrieve_fn, "Consta el DNI del solicitante?")

    assert len(citations) > 0
    assert citations[0]["document_id"] == "DOC-0001"


def test_process_document_raises_pipeline_error_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("DATALAB_API_KEY", raising=False)
    fake_file = tmp_path / "doc.pdf"
    fake_file.write_bytes(b"%PDF-1.4 fake")

    with pytest.raises(pipeline.PipelineError):
        pipeline.process_document(str(fake_file), case_id="EXP-TEST")


def test_build_index_for_case_raises_pipeline_error_if_deps_missing():
    """Solo tiene sentido cuando llama-index/chromadb NO estan instalados
    (p. ej. este sandbox de desarrollo, ver rag/README.md): si ya estan
    instalados en tu maquina, este test se salta -- la integracion real con
    ChromaDB se verifica en tests/rag/test_index_store.py, no aqui."""
    try:
        import llama_index.core  # noqa: F401

        pytest.skip("llama-index instalado: build_index_for_case deberia funcionar de verdad, no fallar.")
    except ModuleNotFoundError:
        pass

    with pytest.raises(pipeline.PipelineError):
        pipeline.build_index_for_case(pipeline.load_demo_case())

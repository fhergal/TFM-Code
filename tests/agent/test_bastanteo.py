from agent import Requirement, RuleBasedJudge, run_bastanteo


def _fake_retrieve_fn(responses):
    """Construye un retrieve_fn falso: responses es un dict query -> citas."""

    def _retrieve(query, top_k):
        return responses.get(query, [])

    return _retrieve


def test_run_bastanteo_all_required_supported_yields_valido():
    requirements = [
        Requirement("REQ-DNI", "Consta DNI", "Cual es el DNI?", requirement_type="required"),
        Requirement("REQ-FIRMA", "Consta firma", "Esta firmado?", requirement_type="required"),
    ]
    retrieve_fn = _fake_retrieve_fn({
        "Cual es el DNI?": [{"document_id": "DOC-0001", "page_number": 1, "score": 0.9, "text": "DNI 123", "bbox": None, "block_ids": ["b1"]}],
        "Esta firmado?": [{"document_id": "DOC-0001", "page_number": 2, "score": 0.8, "text": "firma", "bbox": None, "block_ids": ["b2"]}],
    })

    result = run_bastanteo(requirements, retrieve_fn, judge=RuleBasedJudge(min_score=0.5))

    assert result["bastanteo_gold"]["status"] == "VALIDO"
    assert len(result["bastanteo_evidence"]) == 2
    assert all(e["status"] == "supported" for e in result["bastanteo_evidence"])
    assert result["bastanteo_evidence"][0]["evidence_id"] == "EV-001"
    assert result["bastanteo_evidence"][0]["requirement_id"] == "REQ-DNI"


def test_run_bastanteo_missing_required_yields_incompleto():
    requirements = [
        Requirement("REQ-DNI", "Consta DNI", "Cual es el DNI?", requirement_type="required"),
    ]
    retrieve_fn = _fake_retrieve_fn({})  # sin citas para ninguna query

    result = run_bastanteo(requirements, retrieve_fn)

    assert result["bastanteo_gold"]["status"] == "INCOMPLETO"
    assert "REQ-DNI" in result["bastanteo_gold"]["notes"]
    assert result["bastanteo_evidence"][0]["status"] == "missing"
    assert result["bastanteo_evidence"][0]["linked_document_id"] == ""


def test_run_bastanteo_missing_optional_requirement_still_yields_valido():
    requirements = [
        Requirement("REQ-EXTRA", "Consta anexo opcional", "Hay anexo?", requirement_type="optional"),
    ]
    retrieve_fn = _fake_retrieve_fn({})

    result = run_bastanteo(requirements, retrieve_fn)

    assert result["bastanteo_gold"]["status"] == "VALIDO"


def test_evidence_includes_traceability_fields_from_best_citation():
    requirements = [Requirement("REQ-DNI", "Consta DNI", "Cual es el DNI?")]
    retrieve_fn = _fake_retrieve_fn({
        "Cual es el DNI?": [{
            "document_id": "DOC-0001",
            "page_number": 3,
            "score": 0.95,
            "text": "DNI: 12345678Z",
            "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10, "unit": "pixel"},
            "block_ids": ["DOC-0001-P03-B001"],
        }],
    })

    result = run_bastanteo(requirements, retrieve_fn, judge=RuleBasedJudge(min_score=0.5))
    evidence = result["bastanteo_evidence"][0]

    assert evidence["linked_document_id"] == "DOC-0001"
    assert evidence["linked_page"] == 3
    assert evidence["linked_bbox"] == {"x0": 0, "y0": 0, "x1": 10, "y1": 10, "unit": "pixel"}
    assert evidence["source_block_ids"] == ["DOC-0001-P03-B001"]
    assert evidence["span_text"] == "DNI: 12345678Z"

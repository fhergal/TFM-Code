from ui.naive_retriever import build_naive_retriever
from ui.pipeline import load_demo_case


def test_naive_retriever_finds_dni_block_for_relevant_query():
    case = load_demo_case()
    retrieve_fn = build_naive_retriever(case)

    results = retrieve_fn("Cual es el DNI del solicitante?", top_k=3)

    assert len(results) > 0
    assert results[0]["document_id"] == "DOC-0001"
    assert "12345678Z" in results[0]["text"]


def test_naive_retriever_returns_empty_for_query_with_no_overlap():
    case = load_demo_case()
    retrieve_fn = build_naive_retriever(case)

    results = retrieve_fn("xyz qwerty asdf", top_k=3)

    assert results == []


def test_naive_retriever_respects_top_k():
    case = load_demo_case()
    retrieve_fn = build_naive_retriever(case)

    results = retrieve_fn("solicitante documento firma", top_k=1)

    assert len(results) <= 1


def test_naive_retriever_result_shape_matches_rag_query_citations():
    case = load_demo_case()
    retrieve_fn = build_naive_retriever(case)

    results = retrieve_fn("firma del solicitante", top_k=5)

    assert len(results) > 0
    for key in ("chunk_id", "text", "document_id", "page_number", "section", "block_ids", "bbox", "score"):
        assert key in results[0]

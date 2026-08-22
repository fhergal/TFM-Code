"""Tests de chunking.build_chunks -- puramente logicos, sin dependencias
externas (no requieren llama-index ni chromadb instalados)."""

from __future__ import annotations

from rag.chunking import build_chunks


def _block(block_id, text, section=None, block_type="paragraph", bbox=(0, 0, 10, 10)):
    x0, y0, x1, y1 = bbox
    return {
        "block_id": block_id,
        "block_type": block_type,
        "text": text,
        "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "unit": "pixel"},
        "semantics": {"section": section},
    }


def _document(pages):
    return {"document_id": "DOC-0001", "pages": pages}


def test_groups_consecutive_blocks_of_same_section_into_one_chunk():
    doc = _document([
        {
            "page_number": 1,
            "blocks": [
                _block("b1", "DNI: 123", section="datos_solicitante"),
                _block("b2", "Nombre: Ana", section="datos_solicitante"),
            ],
        }
    ])
    chunks = build_chunks(doc, case_id="EXP-1")

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["section"] == "datos_solicitante"
    assert chunks[0]["metadata"]["block_ids"] == ["b1", "b2"]
    assert "DNI: 123" in chunks[0]["text"] and "Nombre: Ana" in chunks[0]["text"]


def test_section_change_starts_a_new_chunk():
    doc = _document([
        {
            "page_number": 1,
            "blocks": [
                _block("b1", "DNI: 123", section="datos_solicitante"),
                _block("b2", "Motivo: X", section="alegaciones"),
            ],
        }
    ])
    chunks = build_chunks(doc)

    assert len(chunks) == 2
    assert chunks[0]["metadata"]["section"] == "datos_solicitante"
    assert chunks[1]["metadata"]["section"] == "alegaciones"


def test_character_budget_splits_long_same_section_run():
    blocks = [_block(f"b{i}", "x" * 40, section="s1") for i in range(10)]
    doc = _document([{"page_number": 1, "blocks": blocks}])

    chunks = build_chunks(doc, max_chars=100)

    assert len(chunks) > 1
    # ningun chunk debe superar comodamente el presupuesto (con margen por el ultimo bloque que lo dispara)
    for c in chunks:
        assert len(c["text"]) <= 100 + 40


def test_header_block_is_prepended_not_emitted_as_its_own_chunk():
    doc = _document([
        {
            "page_number": 1,
            "blocks": [
                _block("h1", "SECCION A", block_type="section_header"),
                _block("b1", "contenido de la seccion", section="s1"),
            ],
        }
    ])
    chunks = build_chunks(doc)

    assert len(chunks) == 1
    assert chunks[0]["text"].startswith("SECCION A")
    assert "h1" not in chunks[0]["metadata"]["block_ids"]


def test_bbox_envelope_covers_all_blocks_in_chunk():
    doc = _document([
        {
            "page_number": 1,
            "blocks": [
                _block("b1", "a", section="s1", bbox=(10, 10, 50, 50)),
                _block("b2", "b", section="s1", bbox=(40, 40, 90, 90)),
            ],
        }
    ])
    chunks = build_chunks(doc)

    assert chunks[0]["metadata"]["bbox"] == {"x0": 10, "y0": 10, "x1": 90, "y1": 90, "unit": "pixel"}


def test_chunk_id_is_stable_and_scoped_to_document_and_page():
    doc = _document([{"page_number": 2, "blocks": [_block("b1", "x", section="s1")]}])
    chunks = build_chunks(doc)
    assert chunks[0]["chunk_id"] == "DOC-0001-P02-C001"

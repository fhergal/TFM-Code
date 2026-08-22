"""Orquestacion del ciclo de bastanteo: por cada `Requirement`, recupera
citas via `retrieve_fn`, las pasa al `LLMJudge`, y construye
`bastanteo_evidence` + `bastanteo_gold` (definiciones `evidence` del
esquema v1.1 -- ver specs/canonical_document_parse.schema.json).

Deliberadamente NO importa `rag.index_store` ni construye el indice: recibe
`retrieve_fn` ya cerrado sobre un indice concreto (p. ej.
`lambda q, k: rag.query(index, q, top_k=k)`). Esto cumple lo que dice
agent/README.md ("no debe... acoplarse al backend concreto del vector
store") y como efecto practico permite testear el agente entero sin
chromadb ni llama-index instalados (ver tests/agent/test_bastanteo.py).
"""

from __future__ import annotations

from typing import Any, Callable

from .base import Requirement
from .judge import LLMJudge, RuleBasedJudge

RetrieveFn = Callable[[str, int], list[dict[str, Any]]]


def _build_evidence(requirement: Requirement, index: int, status: str, justification_text: str, citation: dict[str, Any] | None) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "evidence_id": f"EV-{index:03d}",
        "requirement_id": requirement.requirement_id,
        "evidence_type": requirement.evidence_type,
        "claim": requirement.claim,
        "status": status,
        "justification_text": justification_text,
    }

    if citation is not None:
        evidence["linked_document_id"] = citation.get("document_id")
        if citation.get("page_number") is not None:
            evidence["linked_page"] = citation["page_number"]
        if citation.get("bbox") is not None:
            evidence["linked_bbox"] = citation["bbox"]
        if citation.get("block_ids") is not None:
            evidence["source_block_ids"] = citation["block_ids"]
        if citation.get("text") is not None:
            evidence["span_text"] = citation["text"]
    else:
        # `linked_document_id` es required (type: string) por el esquema v1.1
        # incluso cuando no hay ninguna cita -- no se puede omitir ni poner a
        # null (ver normalizer/__init__.py _compact() para el mismo problema
        # con campos opcionales). Se usa "" como valor centinela explicito
        # para "sin documento vinculado", en vez de None/null, para que la
        # evidencia siga validando contra el JSON Schema.
        evidence["linked_document_id"] = ""

    return evidence


def _compute_gold(evidence_list: list[dict[str, Any]], requirements: list[Requirement]) -> dict[str, Any]:
    by_id = {r.requirement_id: r for r in requirements}

    contradicted_required = [
        e for e in evidence_list
        if e["status"] == "contradicted" and by_id[e["requirement_id"]].requirement_type == "required"
    ]
    missing_required = [
        e for e in evidence_list
        if e["status"] == "missing" and by_id[e["requirement_id"]].requirement_type == "required"
    ]

    if contradicted_required:
        ids = ", ".join(e["requirement_id"] for e in contradicted_required)
        return {"status": "RECHAZADO", "notes": f"Requisitos obligatorios contradichos: {ids}."}

    if missing_required:
        ids = ", ".join(e["requirement_id"] for e in missing_required)
        return {"status": "INCOMPLETO", "notes": f"Requisitos obligatorios sin evidencia: {ids}."}

    return {"status": "VALIDO", "notes": "Todos los requisitos obligatorios quedan soportados por evidencia."}


def run_bastanteo(
    requirements: list[Requirement],
    retrieve_fn: RetrieveFn,
    judge: LLMJudge | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    """Ejecuta el ciclo de bastanteo sobre una lista de `Requirement`.

    Devuelve un dict con las dos claves de nivel raiz del esquema v1.1 que
    aporta el agente: `bastanteo_evidence` y `bastanteo_gold`. El llamador
    es responsable de fusionarlas en el `case` completo (junto a
    `document_inventory`, construido por `normalizer/`).
    """
    judge = judge or RuleBasedJudge()

    evidence_list = []
    for i, requirement in enumerate(requirements, start=1):
        citations = retrieve_fn(requirement.query, top_k)
        status, justification_text, best_citation = judge.judge(requirement.claim, citations)
        evidence_list.append(_build_evidence(requirement, i, status, justification_text, best_citation))

    gold = _compute_gold(evidence_list, requirements)

    return {"bastanteo_evidence": evidence_list, "bastanteo_gold": gold}

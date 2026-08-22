"""Modulo agent: ciclo de bastanteo (retrieval -> juicio -> evidencia).

No parsea documentos ni conoce el backend del vector store (ver README.md):
recibe un `retrieve_fn` ya cerrado sobre un indice RAG concreto.

Uso tipico:

    from rag import query
    from agent import Requirement, get_judge, run_bastanteo

    requirements = [
        Requirement("REQ-DNI-PRESENTE", "Consta DNI del solicitante",
                    "Consta el DNI del solicitante?"),
    ]
    retrieve_fn = lambda q, k: query(index, q, top_k=k)
    resultado = run_bastanteo(requirements, retrieve_fn, judge=get_judge("rule-based"))
    # resultado = {"bastanteo_evidence": [...], "bastanteo_gold": {...}}
"""

from .base import Requirement
from .bastanteo import run_bastanteo
from .judge import LLMJudge, RuleBasedJudge, get_judge

__all__ = ["Requirement", "run_bastanteo", "LLMJudge", "RuleBasedJudge", "get_judge"]

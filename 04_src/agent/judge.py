"""Juicio de evidencia: dado un `claim` y las citas recuperadas por RAG,
decide si el claim queda `supported`, `contradicted` o `missing`, y redacta
`justification_text`.

Mismo patron adapter/interface que `parser/` (ver `parser/__init__.py` y
`parser/base.py`): una interfaz abstracta `LLMJudge` con backends
intercambiables, para poder pasar de un juicio heuristico (sin coste, sin
red, usado en tests y en la PoC inicial) a un juicio real basado en LLM sin
tocar `bastanteo.py`.

Nota de diseno (igual que en parser/chandra_hf_client.py): el backend por
LLM real (`AnthropicJudge`) es un stub por ahora. Requiere decidir aun si
conviene usar un modelo con buen tool-use sobre texto (el JSON canonico ya
esta extraido, no hace falta VLM aqui) -- ver nota abierta en
`agent/README.md`.
"""

from __future__ import annotations

import abc
from typing import Any


class LLMJudge(abc.ABC):
    """Interfaz de juicio de evidencia. `judge()` no debe lanzar excepciones
    por falta de citas: una lista vacia es una entrada valida (significa
    "no se encontro nada en el expediente") y debe resolver a `missing`."""

    @abc.abstractmethod
    def judge(self, claim: str, citations: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any] | None]:
        """Devuelve (status, justification_text, best_citation_or_None).

        `best_citation_or_None` es la cita elegida como soporte principal
        (o `None` si status == "missing"); `bastanteo.py` la usa para
        rellenar `linked_document_id/linked_page/linked_bbox/source_block_ids/span_text`.
        """
        raise NotImplementedError


class RuleBasedJudge(LLMJudge):
    """Juicio heuristico, sin LLM ni red: usa el score de similitud del
    retriever y un umbral configurable. Pensado para:

    - Tests unitarios deterministas (sin mocks de API ni de red).
    - Una PoC inicial que ya produce `bastanteo_evidence` trazable end-to-end
      antes de decidir/instrumentar el backend LLM real.

    No es el juicio final que se documentara como resultado del TFM -- es
    el escalon minimo que hace el pipeline ejecutable de punta a punta.
    """

    def __init__(self, min_score: float = 0.0):
        self.min_score = min_score

    def judge(self, claim: str, citations: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any] | None]:
        if not citations:
            return (
                "missing",
                f'No se encontro ninguna cita relevante para: "{claim}".',
                None,
            )

        best = max(citations, key=lambda c: c.get("score") or 0.0)
        score = best.get("score") or 0.0

        if score < self.min_score:
            return (
                "missing",
                f'La mejor cita encontrada (score={score:.3f}) no supera el '
                f'umbral minimo ({self.min_score}) para: "{claim}".',
                None,
            )

        snippet = (best.get("text") or "")[:200]
        return (
            "supported",
            f'Se encontro evidencia con score={score:.3f} en '
            f'{best.get("document_id")} (pagina {best.get("page_number")}): "{snippet}"',
            best,
        )


class AnthropicJudge(LLMJudge):
    """Backend futuro: juicio real via LLM (Claude) sobre las citas
    recuperadas, para detectar tambien contradicciones (`contradicted`), no
    solo ausencia/presencia -- algo que `RuleBasedJudge` no puede hacer al
    no "leer" el contenido de la cita.

    Plan de implementacion (no ejecutar hasta decidir modelo/coste):
    1. Prompt con `claim` + citas (texto + metadatos de trazabilidad).
    2. Pedir salida estructurada: {status, justification_text} vinculada a
       una de las citas de entrada (nunca inventar un span_text nuevo).
    3. Registrar `model_name`/`elapsed_seconds` igual que `ParserResult`,
       para poder comparar coste/latencia frente a `RuleBasedJudge` en la
       memoria del TFM.
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "AnthropicJudge no esta implementado todavia. Usa RuleBasedJudge "
            "(backend por defecto) hasta decidir modelo/coste del juicio LLM real."
        )

    def judge(self, claim: str, citations: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any] | None]:
        # Se define solo para que la clase no sea abstracta ante ABCMeta;
        # nunca se ejecuta porque __init__ ya lanza NotImplementedError antes.
        raise NotImplementedError("AnthropicJudge.judge nunca deberia ejecutarse")


_BACKENDS = {
    "rule-based": RuleBasedJudge,
    "anthropic": AnthropicJudge,
}


def get_judge(backend: str = "rule-based", **kwargs) -> LLMJudge:
    if backend not in _BACKENDS:
        raise ValueError(f"Backend de judge desconocido: {backend!r}. Opciones: {list(_BACKENDS)}")
    return _BACKENDS[backend](**kwargs)

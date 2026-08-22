"""Tipos base del agente de bastanteo.

`Requirement` describe UNA comprobación normativa a verificar contra el
expediente (p. ej. "Consta el DNI del solicitante"). El catalogo de
requirements de un tramite concreto vive fuera de este modulo (ver
`agent/catalog.py` para un ejemplo minimo) porque es conocimiento de
dominio (INSS / tipo de prestacion), no logica de agente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RequirementType = Literal["required", "conditional", "optional"]
EvidenceStatus = Literal["supported", "contradicted", "missing"]
EvidenceType = Literal["field", "block", "signature", "stamp", "document"]


@dataclass
class Requirement:
    """Una comprobacion de bastanteo a resolver via retrieval + juicio.

    - `requirement_id`: identificador estable (trazable a `bastanteo_evidence`).
    - `claim`: afirmacion en lenguaje natural que se evalua (campo `claim` del
      esquema v1.1).
    - `query`: pregunta a lanzar contra el indice RAG para recuperar citas.
    - `requirement_type`: si es obligatoria, condicional u opcional -- afecta
      al calculo de `bastanteo_gold.status` (ver bastanteo.py).
    - `evidence_type`: tipo de evidencia esperado segun el esquema v1.1.
    """

    requirement_id: str
    claim: str
    query: str
    requirement_type: RequirementType = "required"
    evidence_type: EvidenceType = "field"

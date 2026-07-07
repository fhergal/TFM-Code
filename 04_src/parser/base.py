"""Interfaz comun (contrato) que debe cumplir cualquier backend de parsing.

IMPORTANTE (ver specs/canonical-document-parse-v1.1.md): este modulo NO
produce el esquema CanonicalDocumentParse v1.1 directamente. Produce la
salida NATIVA del backend (p.ej. markdown/HTML/JSON de Datalab, o el JSON
propio de Chandra si en el futuro se ejecuta en local). Es responsabilidad
de `normalizer/` transformar ParserResult.raw al esquema canonico v1.1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParserResult:
    """Salida nativa de un backend de parsing, antes de normalizar.

    Attributes:
        source_path: ruta del fichero original procesado.
        backend: nombre del backend usado (p.ej. "datalab").
        model_name: nombre/identificador del modelo o servicio subyacente.
        output_format: formato solicitado ("markdown", "html", "json", "chunks").
        raw: contenido devuelto por el backend en ese formato (str o dict).
        page_count: numero de paginas procesadas, si el backend lo informa.
        quality_score: score de calidad de parsing (0-5) si el backend lo informa.
        elapsed_seconds: duracion de la llamada, para trazabilidad/coste.
        extra_metadata: cualquier otro dato util del backend (coste, checkpoint_id...).
    """

    source_path: Path
    backend: str
    model_name: str
    output_format: str
    raw: Any
    page_count: int | None = None
    quality_score: float | None = None
    elapsed_seconds: float | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)


class DocumentParser(ABC):
    """Responsabilidad: ejecutar parsing sobre imagen/PDF y devolver ParserResult.

    No debe (ver 04_src/parser/README.md):
        - decidir chunking,
        - indexar en el vector store,
        - conocer nada del esquema canonico v1.1 (eso es cosa de normalizer/).
    """

    @abstractmethod
    def parse(self, file_path: str | Path, output_format: str = "json") -> ParserResult:
        """Parsea un unico documento (imagen o PDF) y devuelve la salida nativa."""
        raise NotImplementedError

"""Backend de parsing basado en la API gestionada de Datalab (datalab.to).

Por que este backend y no Chandra OCR-2 en local (ver Hilo 01/04 y
0.BaseProyecto.md): el equipo de desarrollo solo dispone de CPU, y Chandra
OCR-2 (4B parametros) es inviable en CPU para una demo. La API de Datalab:
  - no requiere GPU local (decision ya tomada: "API externa durante el
    desarrollo, sustituir despues si es viable 100% local"),
  - ofrece output_format="json" con bloques/bounding boxes, que es
    justo lo que necesita normalizer/ para construir CanonicalDocumentParse v1.1,
  - da $5 de credito gratis, suficiente para el prototipo del TFM.

AVISO PARA LA MEMORIA (importante para la coherencia del TFM, ver revision
de v1.4): la API gestionada de Datalab NO es literalmente "pesos abiertos
de Chandra OCR-2" -- es un servicio propietario gestionado por Datalab que,
segun su propio benchmark, ejecuta una version mejorada internamente (86.7
frente a 85.9 de los pesos abiertos de Chandra 2). Usarla es coherente con
la decision practica de "API externa durante el desarrollo", pero au you
redactar el TFM conviene ser preciso: o bien se documenta esta API como la
usada durante el prototipado (con migracion a pesos abiertos locales via
`chandra-ocr[hf]` como trabajo futuro/variante de despliegue), o bien se
ejecuta tambien una pasada con los pesos abiertos para la evaluacion final.
Cualquiera de las dos opciones evita contradecir el enfoque "open-source"
que defiende el capitulo de Herramientas y modelos.

Requiere:
    pip install datalab-python-sdk python-dotenv
    export DATALAB_API_KEY=... (o ponlo en un archivo .env, ver .env.example)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from .base import DocumentParser, ParserResult

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv es opcional: si no esta instalado, se asume que la
    # variable de entorno ya esta puesta de otra forma (shell, CI, etc.)
    pass


class DatalabParser(DocumentParser):
    """Parser que delega en la API gestionada de Datalab (Marker/Surya/Chandra)."""

    def __init__(self, mode: str = "balanced", api_key: str | None = None) -> None:
        """
        Args:
            mode: "fast" | "balanced" | "accurate". Para documentos administrativos
                escaneados/manuscritos (el caso de este TFM) se recomienda
                "accurate"; "balanced" es un buen punto de partida para iterar rapido.
            api_key: si no se pasa, se lee de la variable de entorno DATALAB_API_KEY.
        """
        try:
            from datalab_sdk import DatalabClient, ConvertOptions
        except ImportError as exc:
            raise ImportError(
                "Falta la dependencia 'datalab-python-sdk'. Instala con:\n"
                "    pip install datalab-python-sdk"
            ) from exc

        self._ConvertOptions = ConvertOptions
        self.mode = mode

        key = api_key or os.getenv("DATALAB_API_KEY")
        if not key:
            raise RuntimeError(
                "No se ha encontrado DATALAB_API_KEY. Copia .env.example a .env, "
                "rellena tu clave (https://www.datalab.to/app/keys) y vuelve a intentarlo."
            )
        self._client = DatalabClient(api_key=key)

    def parse(self, file_path: str | Path, output_format: str = "json") -> ParserResult:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"No existe el fichero a parsear: {file_path}")

        options = self._ConvertOptions(output_format=output_format, mode=self.mode)

        start = time.monotonic()
        result = self._client.convert(str(file_path), options=options)
        elapsed = time.monotonic() - start

        raw = getattr(result, output_format, None)
        if raw is None:
            # Fallback defensivo por si el SDK cambia el nombre del atributo
            raw = getattr(result, "json", None) or getattr(result, "markdown", None)

        return ParserResult(
            source_path=file_path,
            backend="datalab",
            model_name=f"datalab-managed-convert(mode={self.mode})",
            output_format=output_format,
            raw=raw,
            page_count=getattr(result, "page_count", None),
            quality_score=getattr(result, "parse_quality_score", None),
            elapsed_seconds=elapsed,
            extra_metadata={
                "cost_breakdown": getattr(result, "cost_breakdown", None),
                "checkpoint_id": getattr(result, "checkpoint_id", None),
            },
        )

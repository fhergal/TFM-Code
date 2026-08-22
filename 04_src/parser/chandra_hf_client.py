"""Backend PENDIENTE: Chandra OCR-2 en local via HuggingFace Transformers.

Esto es justo lo que necesitas para la comparativa que comentaste (API
gestionada de Datalab vs. pesos abiertos de Chandra: rendimiento/calidad
frente a coste) -- ver Innovacion 4 del Hilo 01 ("Eficiencia y despliegue en
entornos reales"), que encaja perfectamente con esta comparativa.

Por que esta clase todavia no funciona: requiere GPU (o mucha paciencia en
CPU: Chandra OCR-2 tiene 4B parametros) y `pip install chandra-ocr[hf]`
(incluye torch). En cuanto tengas acceso a GPU (local nueva, AWS con GPU, o
Colab/similar), implementa `parse()` aqui siguiendo el mismo contrato que
`datalab_client.DatalabParser`, y podras comparar ambos backends con el
MISMO documento y el MISMO codigo de `normalizer/`, cambiando solo
`get_parser("datalab")` <-> `get_parser("chandra-hf")`.

Boceto de implementacion (a completar cuando haya GPU disponible):

    from chandra import ChandraOCR  # nombre real del import a confirmar
                                     # contra la version instalada de chandra-ocr[hf]
    self._model = ChandraOCR.from_pretrained("datalab-to/chandra-ocr-2")
    ...
    output = self._model.predict(file_path, output_format=output_format)

Metricas a registrar para la comparativa (mismo documento, ambos backends):
    - tiempo total (elapsed_seconds, ya lo captura ParserResult),
    - quality_score / ANLS sobre el mismo ground truth,
    - coste: Datalab = cost_breakdown de la respuesta; Chandra local =
      coste de la instancia/hora (GPU) x tiempo, o 0 si es hardware propio,
    - consumo de VRAM (si se ejecuta en GPU propia o instancia monitorizada).
"""

from __future__ import annotations

from pathlib import Path

from .base import DocumentParser, ParserResult


class ChandraHFParser(DocumentParser):
    """Placeholder: Chandra OCR-2 local via `chandra-ocr[hf]`. No implementado
    todavia (requiere GPU). Ver docstring del modulo para el plan."""

    def __init__(self, device: str = "cuda") -> None:
        self.device = device
        raise NotImplementedError(
            "ChandraHFParser todavia no esta implementado (pendiente de GPU). "
            "Ver 04_src/parser/chandra_hf_client.py para el plan de implementacion "
            "y usa get_parser('datalab') mientras tanto."
        )

    def parse(self, file_path: str | Path, output_format: str = "json") -> ParserResult:
        raise NotImplementedError

"""
Modulo parser: convierte imagen/PDF en la salida NATIVA del backend de parsing
(por defecto, la API gestionada de Datalab/Chandra). No decide chunking ni
indexa nada en el vector store -- eso vive en el modulo `normalizer` y `rag`.

Uso tipico:

    from parser import get_parser

    parser = get_parser()  # backend "datalab" por defecto
    raw_output = parser.parse("expediente/solicitud_01.pdf")
"""

from .base import DocumentParser, ParserResult
from .chandra_hf_client import ChandraHFParser
from .datalab_client import DatalabParser

_BACKENDS = {
    "datalab": DatalabParser,
    # Pendiente de GPU (ver chandra_hf_client.py): registrado ya para que la
    # futura comparativa Datalab-vs-Chandra-local solo requiera cambiar este
    # string, sin tocar normalizer/ ni el resto del pipeline.
    "chandra-hf": ChandraHFParser,
}


def get_parser(backend: str = "datalab", **kwargs) -> DocumentParser:
    """Factory: devuelve una instancia de DocumentParser para el backend pedido.

    Args:
        backend: nombre del backend registrado en _BACKENDS ("datalab" por defecto).
        **kwargs: argumentos que se pasan al constructor del backend concreto.
    """
    try:
        cls = _BACKENDS[backend]
    except KeyError as exc:
        disponibles = ", ".join(sorted(_BACKENDS))
        raise ValueError(
            f"Backend de parser desconocido: {backend!r}. Disponibles: {disponibles}"
        ) from exc
    return cls(**kwargs)


__all__ = ["DocumentParser", "ParserResult", "get_parser"]

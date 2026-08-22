"""Mini-ejemplo AUTOCONTENIDO para enseñar "cómo se prueba Chandra vía Datalab".

Deliberadamente NO usa el adaptador `DocumentParser`/`get_parser()` del resto
del proyecto (ver parser/datalab_client.py) -- es solo para mostrar, en un
par de pantallazos, el gesto minimo: API key -> convertir un documento ->
ver el resultado. Nada mas.

Uso:
    pip install datalab-python-sdk python-dotenv
    export DATALAB_API_KEY=tu_clave      # o ponla en un .env (ver .env.example)
    python quickstart_datalab_chandra.py ruta/a/un/documento.pdf

Que hace Datalab aqui (para la presentacion): "convert" es el endpoint que
por debajo usa Marker + Surya + (segun el tipo de bloque) Chandra OCR-2 para
pasar de PDF/imagen a texto/markdown/JSON estructurado por bloques.
"""

from __future__ import annotations

import os
import sys
import time

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # opcional: si no esta instalado, se asume la variable ya esta puesta


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Uso: python {sys.argv[0]} ruta/a/documento.pdf")
        sys.exit(1)

    file_path = sys.argv[1]

    api_key = os.getenv("DATALAB_API_KEY")
    if not api_key:
        print("Falta DATALAB_API_KEY. Consigue una gratis en https://www.datalab.to/app/keys")
        sys.exit(1)

    from datalab_sdk import ConvertOptions, DatalabClient

    client = DatalabClient(api_key=api_key)

    # mode="accurate": mejor calidad para documentos administrativos
    # escaneados/manuscritos (frente a "fast"/"balanced"), a costa de mas tiempo.
    options = ConvertOptions(output_format="markdown", mode="accurate")

    print(f"Enviando '{file_path}' a Datalab (mode=accurate)...")
    start = time.monotonic()
    result = client.convert(file_path, options=options)
    elapsed = time.monotonic() - start

    print(f"\nListo en {elapsed:.1f}s")
    print(f"Paginas: {getattr(result, 'page_count', '?')}")
    print(f"Score de calidad: {getattr(result, 'parse_quality_score', '?')}")
    print("\n--- Primeros 1000 caracteres del resultado (markdown) ---\n")
    print((result.markdown or "")[:1000])


if __name__ == "__main__":
    main()

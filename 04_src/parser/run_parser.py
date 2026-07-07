"""Script de prueba manual para el Paso 1 de la PoC minima (ver hilo-04):

    imagen/PDF -> Chandra (via API Datalab) -> JSON

Uso:
    python 04_src/parser/run_parser.py ruta/al/documento.pdf
    python 04_src/parser/run_parser.py ruta/al/documento.pdf --mode accurate --format markdown

Guarda la salida cruda en 03_data/generated/parsed/<nombre>.json (o .md/.html
segun --format) para poder inspeccionarla antes de escribir el normalizador.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permite ejecutar el script directamente (python 04_src/parser/run_parser.py ...)
# sin depender de que el paquete este instalado con `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser import get_parser  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", help="Ruta al documento (imagen o PDF) a parsear")
    ap.add_argument("--mode", default="balanced", choices=["fast", "balanced", "accurate"])
    ap.add_argument("--format", default="json", choices=["markdown", "html", "json", "chunks"])
    ap.add_argument(
        "--out-dir",
        default="03_data/generated/parsed",
        help="Carpeta donde guardar la salida cruda (por defecto 03_data/generated/parsed)",
    )
    args = ap.parse_args()

    parser = get_parser("datalab", mode=args.mode)
    result = parser.parse(args.file, output_format=args.format)

    print(f"Backend:        {result.backend}")
    print(f"Modelo:         {result.model_name}")
    print(f"Paginas:        {result.page_count}")
    print(f"Quality score:  {result.quality_score}")
    print(f"Tiempo (s):     {result.elapsed_seconds:.2f}" if result.elapsed_seconds else "")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = "json" if args.format == "json" else ("md" if args.format == "markdown" else args.format)
    out_path = out_dir / f"{Path(args.file).stem}.{ext}"

    if isinstance(result.raw, (dict, list)):
        out_path.write_text(json.dumps(result.raw, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        out_path.write_text(str(result.raw), encoding="utf-8")

    print(f"\nSalida cruda guardada en: {out_path}")
    print("Siguiente paso: escribir 04_src/normalizer/ para convertir esta salida")
    print("nativa al esquema CanonicalDocumentParse v1.1 (ver specs/).")


if __name__ == "__main__":
    main()

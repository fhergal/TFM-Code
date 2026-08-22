"""Actualiza figura2_comparativa_baselines.py con datos reales de evaluación.

Lee resultados_evaluacion.json y sustituye los valores PLACEHOLDER
en figura2_comparativa_baselines.py por los valores reales obtenidos.

Luego genera la imagen PNG lista para insertar en la memoria.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def update_figura2_script(
    figura2_path: Path,
    f1: float,
    anls: float,
    latencia_ms: float,
    vram_gb: float,
) -> str:
    """
    Lee figura2_comparativa_baselines.py y sustituye los PLACEHOLDER.
    Retorna el contenido actualizado.
    """
    with open(figura2_path) as f:
        content = f.read()

    # Sustituir los valores PLACEHOLDER en el script
    replacements = {
        '"f1": PLACEHOLDER_F1': f'"f1": {f1:.3f}',
        '"f1": 0.00  # PLACEHOLDER_F1': f'"f1": {f1:.3f}',
        'PLACEHOLDER_F1': f'{f1:.3f}',
        'PLACEHOLDER_ANLS': f'{anls:.3f}',
        'PLACEHOLDER_LATENCIA': f'{latencia_ms:.0f}',
        'PLACEHOLDER_VRAM': f'{vram_gb:.2f}',
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    return content


def main():
    parser = argparse.ArgumentParser(
        description="Actualiza Figura 2 con resultados de evaluación"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="resultados_evaluacion.json",
        help="Archivo con resultados de evaluación",
    )
    parser.add_argument(
        "--figura2-script",
        type=str,
        default="figura2_comparativa_baselines.py",
        help="Script de Figura 2 a actualizar",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="figura2_comparativa_baselines_ACTUALIZADA.py",
        help="Script actualizado (salida)",
    )
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ {input_file} no encontrado")
        return 1

    figura2_path = Path(args.figura2_script)
    if not figura2_path.exists():
        print(f"❌ {figura2_path} no encontrado")
        return 1

    # Cargar resultados
    print(f"📖 Leyendo {input_file}...")
    with open(input_file) as f:
        data = json.load(f)

    figura2_vals = data["figura2_data"]
    f1 = figura2_vals["F1_macro"] / 100
    anls = figura2_vals["ANLS"] / 100
    latencia = figura2_vals["Latencia_ms"]
    vram = figura2_vals["VRAM_GB"]

    print(f"\n📊 Valores a insertar:")
    print(f"   F1 macro:    {f1:.3f} ({f1*100:.1f}%)")
    print(f"   ANLS:        {anls:.3f} ({anls*100:.1f}%)")
    print(f"   Latencia:    {latencia:.0f} ms")
    print(f"   VRAM:        {vram:.2f} GB")

    # Actualizar script
    print(f"\n✏️  Actualizando {figura2_path}...")
    updated_content = update_figura2_script(figura2_path, f1, anls, latencia, vram)

    # Guardar script actualizado
    out_path = Path(args.out)
    with open(out_path, "w") as f:
        f.write(updated_content)

    print(f"✅ Script guardado en {out_path}")

    # Generar imagen (opcional, si tienes matplotlib disponible)
    print(f"\n🖼️  Para generar la imagen PNG, ejecuta:")
    print(f"   python {out_path}")
    print(f"\n   O en el script de memoria, importa y ejecuta:")
    print(f"   from figura2_comparativa_baselines_ACTUALIZADA import main")
    print(f"   main()  # Genera figura2_comparativa_baselines.png")

    return 0


if __name__ == "__main__":
    exit(main())

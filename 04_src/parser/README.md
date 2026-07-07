# 04_src/parser

Responsabilidad: ejecutar el parsing sobre imagen/PDF y devolver la salida nativa + metadatos de ejecución (`ParserResult`).

No debe: decidir chunking ni indexar en el vector store (eso vive en `rag/`), ni conocer el esquema canónico v1.1 (eso es cosa de `normalizer/`).

Contrato de salida final esperado (tras pasar por `normalizer/`): ver `../../specs/canonical-document-parse-v1.1.md`.

## Backend implementado: API gestionada de Datalab

Dado que el equipo solo dispone de CPU (sin GPU local), Chandra OCR-2 (4B parámetros) es inviable en local para una demo. Se usa la **API gestionada de Datalab** (`datalab-python-sdk`), que expone `output_format="json"` con bloques y bounding boxes — justo la entrada que necesita `normalizer/`.

**Aviso para la memoria del TFM:** esta API no son literalmente los pesos abiertos de Chandra OCR-2, es un servicio propietario de Datalab (que, según su propio benchmark, rinde incluso mejor: 86.7 vs 85.9 del modelo abierto). Es coherente con la decisión ya tomada de "API externa durante el desarrollo", pero para no contradecir el discurso "open-source" del capítulo de Herramientas y modelos, documentar esto explícitamente en la memoria (como elección de prototipado, con migración a pesos abiertos locales o evaluación adicional con pesos abiertos como trabajo futuro).

### Instalación y configuración

```bash
pip install -e .          # instala el proyecto en modo editable (ver pyproject.toml)
cp .env.example .env      # y rellena DATALAB_API_KEY (https://www.datalab.to/app/keys, $5 gratis)
```

### Uso rápido

```python
from parser import get_parser

parser = get_parser("datalab", mode="balanced")  # o mode="accurate" para docs difíciles
result = parser.parse("expediente/solicitud_01.pdf", output_format="json")

print(result.raw)             # bloques/bboxes nativos de Datalab
print(result.quality_score)   # 0-5, úsalo como gate: <3.0 -> reintentar con mode="accurate"
```

O desde la línea de comandos, para probar sin escribir código:

```bash
python 04_src/parser/run_parser.py ruta/al/documento.pdf --mode accurate --format json
```

Guarda la salida cruda en `03_data/generated/parsed/` para poder inspeccionarla antes de escribir el normalizador (siguiente paso).

### Tests

```bash
pytest tests/parser/ -v
```

Los tests simulan `datalab_sdk` (no llaman a la API real, no gastan crédito).

### Backends futuros

La interfaz `DocumentParser` (`base.py`) permite añadir otros backends sin tocar el resto del pipeline: por ejemplo `chandra-ocr[hf]` en local si en algún momento hay GPU disponible, o `dots.ocr` como alternativa ligera. Basta con crear una clase que implemente `parse()` y registrarla en `_BACKENDS` (`__init__.py`).

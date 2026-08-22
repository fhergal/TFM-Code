# 04_src/normalizer

Responsabilidad: convertir la salida NATIVA del parser (`parser.base.ParserResult`) al esquema canónico `CanonicalDocumentParse v1.1` (`../../specs/canonical-document-parse-v1.1.md` / `canonical_document_parse.schema.json`), validar estructura y tipos, y añadir metadatos mínimos obligatorios.

No debe: llamar al LLM ni acoplarse a la UI.

Nota: usa el esquema v1.1 unificado como formato de salida, no el borrador plano (`doc_id/page/block_id/type/...`) descrito en el hilo de decisiones de implementación — ese borrador quedó fusionado dentro de v1.1 (ver tabla de mapeo en el spec).

## ⚠️ Aviso sobre el mapeo de bloques (`marker_blocks.py`)

Datalab no publica en su OpenAPI el esquema interno exacto del campo `json` de `/convert` (lo tipan como "object" genérico). El mapeo implementado asume la forma pública de bloques del proyecto Marker de Datalab (árbol `Document -> Page -> bloques` con `block_type`, `children`, `bbox`/`polygon`, `html`). **Antes de confiar en esto con datos reales**: ejecuta `run_parser.py` con tu API key real, guarda el JSON crudo, y compara con `BLOCK_TYPE_MAP` / `_get_bbox` / `_get_text` en `marker_blocks.py`. Ajusta lo que no coincida.

## Uso

```python
from parser import get_parser
from normalizer import build_document_entry, build_case_envelope, validate

p = get_parser("datalab")
raw = p.parse("solicitud_01.pdf", output_format="json")

doc = build_document_entry(raw, document_id="DOC-0001", document_type_pred="solicitud")
case = build_case_envelope(
    case_id="EXP-2026-0001",
    procedure_type="prestacion_inss",
    documents=[doc],
    parser_result=raw,
)
validate(case, part="case")  # lanza jsonschema.ValidationError si no cumple v1.1
```

Nota: `document_type_pred` es **obligatorio** en el esquema v1.1. Si todavía no existe un clasificador (paso del agente, más adelante), tendrás que pasarlo tú a mano o dejar el caso sin validar hasta ese paso.

## Tests

```bash
pytest tests/normalizer/ -v
```

Usan un árbol de bloques **sintético** (no una respuesta real de la API) — ver el aviso arriba.

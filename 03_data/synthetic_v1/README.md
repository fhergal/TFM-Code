# Dataset sintético BADA v1 — Fase 1 (Faker + reglas de negocio)

Generado por `03_data/generators/generador_bada.py`. Reproducible con `--seed 42`.

## Contenido

- **20 expedientes** (`EXP-SYN-0001.json` … `EXP-SYN-0020.json`), cada uno conforme al
  esquema `CanonicalDocumentParse v1.1` (`specs/canonical_document_parse.schema.json`),
  validado al 100% (`jsonschema.Draft7Validator`).
- `manifest.json`: índice con `case_id`, escenario, `status_gold` y nº de documentos.

## Distribución de escenarios (semilla 42)

| Escenario | Descripción | Nº casos |
|---|---|---|
| `valido` | Todos los requisitos obligatorios presentes y coherentes | 12 |
| `incompleto` | Falta al menos un documento obligatorio (DOC-0002 o DOC-0004) | 5 |
| `rechazado` | El DNI del solicitante no coincide con el del certificado de nacimiento | 3 |

Los documentos condicionales (vínculo conyugal, discapacidad) se incluyen de forma
independiente al escenario, con probabilidad 35% y 25% respectivamente, para simular
la variabilidad real de expedientes con o sin cónyuge/dependientes a cargo.

## Coherencia garantizada

- **DNI/NUSS/nombre** idénticos en todos los documentos del mismo expediente, salvo en
  los casos `rechazado`, donde la discrepancia de DNI es la contradicción intencional
  que el agente debe detectar.
- **`bastanteo_gold` calculado de forma determinista**, no asignado a mano: se deriva de
  qué documentos están realmente presentes en `document_inventory`. El propio generador
  verifica esta consistencia al final de la ejecución y aborta (`exit 1`) si detecta un
  caso `incompleto`/`rechazado` cuyo gold calculado no coincide con el escenario
  pretendido — así no se cuela un dataset de evaluación silenciosamente incorrecto.

## Limitación conocida (Fase 1 de 4)

Este dataset es **solo texto estructurado** (bloques con texto sintético, sin imagen ni
degradación visual). Sirve para evaluar:

- ✅ Clasificación documental (`document_type_pred` vs. `document_type_gold`)
- ✅ Detección de expedientes incompletos/con contradicciones (el agente de bastanteo)
- ✅ Extracción de campos clave (DNI, NUSS, fecha) sobre texto limpio

Pero **no** sirve todavía para evaluar el parser visual (Chandra OCR-2 / dots.ocr /
Nemotron-Parse) ni la robustez ante degradación visual (H1, parte de la evaluación de
§4), porque no hay imagen real de la que partir. Eso corresponde a las fases
siguientes del pipeline, no ejecutadas en esta sesión:

- **Fase 2 (LayoutDM):** variabilidad estructural del layout por tipo de documento.
- **Fase 3 (SynthDoG):** render del JSON gold a imagen/PDF.
- **Fase 4 (augmentación):** ruido, dobleces, sellos, compresión.

## Regenerar / ampliar

```bash
cd 03_data/generators
python3 generador_bada.py --n 50 --out ../synthetic_v1 --seed 42
```

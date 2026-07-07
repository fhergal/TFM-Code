# 03_data

Dataset sintético, esquemas y guías de etiquetado.

- `raw/` y `generated/` están excluidos de git (ver `.gitignore`): son artefactos pesados, no código.
- El esquema de referencia para cualquier documento generado es `../specs/canonical-document-parse-v1.1.md`.
- Cada lote sintético debe registrar: script/versión usado, fecha de generación, número de expedientes y semilla aleatoria, para reproducibilidad.

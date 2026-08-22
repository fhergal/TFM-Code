# ADR-002 · `CanonicalDocumentParse v1.1` como contrato único del sistema

**Estado:** Aceptada
**Fecha:** Junio 2026 (Fase 0 — unificación de esquemas)
**Decisores:** Fer (autor), asistido por Claude
**Requisitos afectados:** REQ-2.1, REQ-2.4, y transversalmente todos los demás

---

## Contexto

El sistema tiene cinco componentes (parser, normalizador, RAG, agente, UI) y tres consumidores
de datos adicionales (dataset sintético, ground truth, pipeline de evaluación). Sin un contrato
común, cada pareja de componentes desarrollaría su propio formato de intercambio, con dos efectos
tóxicos ya identificados en el Hilo 02:

1. **Divergencia experimentación/producto:** el dataset gold y la salida real del sistema dejarían
   de ser comparables, invalidando las métricas.
2. **Acoplamiento al proveedor:** evaluar un parser distinto obligaría a rehacer el marco de pruebas.

Agravante detectado en la revisión de la memoria v1.4: existían **dos versiones divergentes** del
esquema (la del Anexo B del documento y la del Hilo 02), con nombres de campo incompatibles.

## Decisión

Se adopta **`CanonicalDocumentParse v1.1`** como representación interna única, formalizada en un
**JSON Schema validable** (`specs/canonical_document_parse.schema.json`) y documentada en
`specs/canonical-document-parse-v1.1.md`. La v1.1 reconcilia las dos versiones divergentes previas
mediante una tabla de mapeo explícita.

Jerarquía obligatoria:

```
case → document_inventory[] → pages[] → blocks[] → extracted_fields[] → bastanteo_evidence[]
```

Reglas asociadas:

- **Todo** módulo consume y produce este contrato. Ninguno consume la salida nativa de otro.
- La ground truth del dataset es una instancia "gold" **del mismo esquema**, no un formato aparte.
- El vocabulario de `block_type` es **cerrado** (15 valores) y estable.
- La validación con `jsonschema` se ejecuta en los tests, no solo en runtime.

## Consecuencias

**Positivas**
- Cualquier parser puede evaluarse contra la misma ground truth sin rediseñar nada.
- El chunker del RAG puede agrupar por `semantics.section` porque sabe que ese campo siempre existe.
- El agente puede anclar evidencias a `block_id` + `page` + `bbox` porque el contrato lo garantiza.
- Las métricas (F1 macro de clasificación, ANLS de extracción, grounding) se calculan sobre una
  única estructura, tanto para el sistema como para el gold.

**Negativas / coste asumido**
- Cada nuevo backend de parser exige escribir su adaptador de mapeo.
- Los cambios de esquema son costosos: obligan a migrar tests, fixtures y dataset a la vez.
  Por eso el esquema está versionado (`schema_version`) desde el primer día.

**Efecto secundario valioso (comprobado)**
La validación estricta del schema **detectó un bug real** que llevaba tiempo enmascarado: un fixture
de test usaba `quality_score=4.1` donde el schema restringe `confidence_global` a [0, 1]. El fallo
estaba oculto porque un artefacto del entorno impedía que la validación llegara a ejecutarse.
Es evidencia directa del valor de tener el contrato como schema ejecutable y no como prosa.

## Alternativas consideradas y descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Usar el formato nativo de Marker/Datalab como contrato | Acopla todo el sistema al proveedor; imposibilita la comparativa (ADR-001) |
| Texto plano + metadatos sueltos | Pierde `bbox` y jerarquía → imposible el grounding espacial, que es el núcleo de la propuesta |
| Modelos Pydantic como única fuente de verdad | Válido en Python, pero no sirve como contrato de intercambio para el dataset ni para consumidores externos. Se mantiene Pydantic como opción complementaria, con el JSON Schema como referencia normativa |
| Esquema laxo, campos opcionales por defecto | Reintroduce la divergencia que precisamente se quería eliminar |

## Referencias

- `specs/canonical_document_parse.schema.json`, `specs/canonical-document-parse-v1.1.md`
- `04_src/normalizer/marker_blocks.py`
- `04_src/ui/sample_case.json` (instancia real: expediente BADA de 6 documentos)
- Hilo 02 — "convertir `CanonicalDocumentParse` en el contrato único de todo el sistema"

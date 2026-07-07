# CanonicalDocumentParse v1.1 — Esquema unificado

**Estado:** propuesta para cierre de Fase 0 (entrega jueves).
**Sustituye a:** dos versiones divergentes del mismo contrato:
- La definida en el Hilo-02 (Dataset / Ground Truth / Metodología de Evaluación).
- La definida en el Anexo B del TFM v1.4 (Especificaciones por componente SpecDD).

## 0. Por qué hace falta esta unificación

Ambos hilos describen el mismo contrato — la representación estructurada que conecta parser, RAG, agente de bastanteo y evaluación — pero con vocabularios distintos para los mismos conceptos (`expediente_id` vs `case_id`, `documents` vs `document_inventory`, `bastanteo_evidence` vs evidencias ligadas a `requirement_id`, etc.). Si el código (TFM-Code) empieza a implementarse contra cualquiera de las dos versiones sin resolver esto antes, el dataset sintético, el parser y el agente dejarán de ser intercambiables entre sí — justo el problema que SpecDD está pensado para evitar.

Esta v1.1 es la única versión canónica a partir de ahora. Sustituye tanto al bloque JSON del Anexo B del TFM v1.4 como a la lista de atributos del Hilo-02. Ambos quedan como historial/justificación, no como referencia activa.

## 1. Criterio de unificación

Regla general aplicada: se conserva el nombre del Hilo-02 cuando es más explícito o más alineado con el dominio de bastanteo (p. ej. `is_required`, `document_date`, `requirement_id`), y se conserva la estructura del Anexo B del v1.4 cuando aporta más detalle operativo ya pensado para RAG/agente (p. ej. el bloque `parser`, `quality`, `validation`, `bbox` con `x0/y0/x1/y1`). Ningún campo propuesto en cualquiera de los dos hilos se ha descartado: los que faltaban en una versión se han incorporado a la unificada.

## 2. Tabla de mapeo (trazabilidad)

| Concepto | Nombre en v1.4 (Anexo B) | Nombre en Hilo-02 | Nombre unificado v1.1 |
|---|---|---|---|
| Id. de expediente | `expediente_id` | `case_id` | **`case_id`** |
| Tipo de trámite | `case_context.procedure_type` | `procedure_type` | **`procedure_type`** (nivel raíz) |
| Lista de documentos | `documents[]` | `document_inventory[]` | **`document_inventory[]`** |
| Mapa esperado (oblig./opc.) | *(ausente)* | `expected_document_map` | **`expected_document_map`** *(incorporado)* |
| Decisión final de expediente | *(implícita en salida agente)* | `bastanteo_gold` | **`bastanteo_gold`** *(incorporado)* |
| Fuente/canal del documento | `origin.source_kind` | `source_format` | **`origin.source_format`** |
| Canal de entrada | `document_metadata.channel` | `input_channel` | **`origin.input_channel`** |
| Fecha del documento | *(ausente)* | `document_date` | **`document_metadata.document_date`** *(incorporado)* |
| Idioma principal | `document_metadata.main_language` | `language` | **`document_metadata.language`** |
| Estado de firma | `document_metadata.signature_state` | `signature_status` | **`document_metadata.signature_status`** |
| Orden de lectura | `page_anchor.reading_order_index` | `reading_order` | **`reading_order`** |
| Valor bruto del campo | *(ausente)* | `field_value_raw` | **`field_value_raw`** *(incorporado)* |
| Obligatoriedad del campo | `required` | `is_required` | **`is_required`** |
| Localización directa del campo | *(implícita vía `source_block_ids`)* | `field_bbox` | **`field_bbox`** *(incorporado, además de `source_block_ids`)* |
| Vínculo normativo de la evidencia | *(ausente)* | `requirement_id` | **`requirement_id`** *(incorporado)* |
| Tipo de evidencia | *(ausente)* | `evidence_type` | **`evidence_type`** *(incorporado)* |
| Documento/página de la evidencia | `source_document_id` / `source_page` | `linked_document_id` / `linked_page` | **`linked_document_id`** / **`linked_page`** |
| Coordenadas de la evidencia | *(ausente)* | `linked_bbox` | **`linked_bbox`** *(incorporado)* |
| Texto de justificación | *(implícito en `claim`)* | `justification_text` | se mantienen **ambos**: `claim` (afirmación evaluada) + `justification_text` (explicación) |

Todo lo que ya existía en el Anexo B del v1.4 y no aparece en esta tabla se mantiene sin cambio de nombre (p. ej. `schema_version`, `parser`, `bbox.{x0,y0,x1,y1,unit}`, `quality`, `validation`).

## 3. Esquema completo (ejemplo anotado)

```json
{
  "schema_version": "1.1",
  "case_id": "EXP-2026-0001",
  "procedure_type": "prestacion_inss",
  "source_batch_id": "lote-sintetico-001",
  "created_at": "2026-07-09T12:00:00Z",

  "parser": {
    "canonical_parser": "chandra-ocr-2",
    "parser_family": "vlm_ocr_free",
    "model_version": "4b",
    "raw_output_format": "json",
    "confidence_global": 0.92
  },

  "case_context": {
    "domain": "bastanteo_administrativo",
    "language_expected": ["es"],
    "country": "ES"
  },

  "expected_document_map": [
    { "document_type": "solicitud", "required": true },
    { "document_type": "id_dni_nie", "required": true },
    { "document_type": "fam_libro_familia", "required": "condicional" }
  ],

  "document_inventory": [
    {
      "document_id": "DOC-0001",
      "document_type_pred": "solicitud",
      "document_type_gold": "solicitud",
      "origin": {
        "source_format": "scan",
        "file_name": "solicitud_01.pdf",
        "mime_type": "application/pdf",
        "page_count": 3,
        "input_channel": "registro_presencial"
      },
      "document_metadata": {
        "issuer_org": "INSS",
        "document_date": "2026-06-20",
        "language": "es",
        "signature_status": "firma_manuscrita",
        "legibility_level": "media",
        "template_version": "v2025"
      },
      "pages": [
        {
          "page_number": 1,
          "page_size": { "width": 2480, "height": 3508, "unit": "pixel" },
          "blocks": [
            {
              "block_id": "DOC-0001-P01-B012",
              "block_type": "form_field",
              "label": "DNI",
              "text": "12345678Z",
              "normalized_text": "12345678Z",
              "bbox": { "x0": 412, "y0": 826, "x1": 890, "y1": 904, "unit": "pixel" },
              "reading_order": 12,
              "semantics": {
                "entity_type": "dni",
                "section": "datos_del_solicitante",
                "required_for_bastanteo": true
              },
              "quality": {
                "confidence": 0.97,
                "ocr_noise_level": "low",
                "handwritten": false,
                "crossed_out": false
              }
            }
          ]
        }
      ],
      "extracted_fields": [
        {
          "field_id": "F-DNI-SOLICITANTE",
          "field_name": "dni_solicitante",
          "field_value": "12345678Z",
          "field_value_raw": "12345678 Z",
          "confidence": 0.97,
          "source_block_ids": ["DOC-0001-P01-B012"],
          "field_bbox": { "x0": 412, "y0": 826, "x1": 890, "y1": 904, "unit": "pixel" },
          "is_required": true,
          "validation": { "status": "valid", "rule": "dni_checksum_es" }
        }
      ]
    }
  ],

  "bastanteo_evidence": [
    {
      "evidence_id": "EV-001",
      "requirement_id": "REQ-DNI-PRESENTE",
      "evidence_type": "field",
      "claim": "Consta DNI del solicitante",
      "status": "supported",
      "linked_document_id": "DOC-0001",
      "linked_page": 1,
      "linked_bbox": { "x0": 412, "y0": 826, "x1": 890, "y1": 904, "unit": "pixel" },
      "source_block_ids": ["DOC-0001-P01-B012"],
      "span_text": "12345678Z",
      "justification_text": "El campo DNI aparece legible y coincide con el formato esperado."
    }
  ],

  "bastanteo_gold": {
    "status": "VALIDO",
    "notes": "Expediente completo según el mapa documental v1."
  }
}
```

## 4. Tipos de bloque y entidad semántica (sin cambios respecto al v1.4)

- **`block_type`:** `title`, `section_header`, `paragraph`, `form_field`, `key_value`, `table`, `table_row`, `table_cell`, `checkbox`, `signature`, `stamp`, `image_region`, `footer`, `header`, `free_note`.
- **`entity_type`:** `dni`, `nuss`, `person_name`, `address`, `date`, `document_number`, `issuer_org`, `procedure_type`, `signature_presence`, `stamp_presence`, `mandatory_clause`.
- **`evidence_type`** *(nuevo, de Hilo-02)*: `field`, `block`, `signature`, `stamp`, `document`.
- **`bastanteo_gold.status`** / **`document_type_pred/gold` en expediente:** `VALIDO`, `INCOMPLETO`, `RECHAZADO`.

## 5. JSON mínimo viable (para el prototipo, sin cambios de fondo respecto al v1.4)

- **V1 (obligatoria):** `case_id`, `document_inventory[].document_id`, `.document_type_pred`, `pages[].blocks[].block_id/block_type/text/bbox`, `quality.confidence`, `extracted_fields[].field_name/field_value/source_block_ids`.
- **V2 (deseable):** `expected_document_map`, `bastanteo_gold`, `bastanteo_evidence[].requirement_id`, `reading_order`, `field_value_raw`, `field_bbox`, `document_type_gold`.

## 6. Qué hay que actualizar tras esta unificación

1. **TFM v1.4, Anexo B** — sustituir el bloque JSON actual por el de este documento (o enlazar a él) y renombrar los campos según la tabla del punto 2. (Fer se encarga de esto en el Word.)
2. **Hilo-02** — queda como el origen conceptual de `expected_document_map`, `bastanteo_gold`, `requirement_id`, etc.; no requiere cambios, solo se marca como consolidado en v1.1.
3. **TFM-Code** — cualquier modelo Pydantic / dataclass / validación JSON Schema debe partir de este archivo, no de las dos versiones anteriores. Ver `canonical_document_parse.schema.json` en esta misma carpeta para validación programática.
4. **Curso SpecDD (Hilo 02 del curso / LIDR-Code)** — si el proyecto del curso referencia el mismo contrato, debe apuntar también a esta v1.1 para que ambas vistas (TFM y curso) compartan un único contrato, tal como se planteó en `0.BaseProyecto.md`.

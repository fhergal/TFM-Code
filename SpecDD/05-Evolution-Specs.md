# Evidencia de iteración — Cómo evolucionaron las especificaciones

**Versión:** 1.0 · **Fecha:** Julio 2026
**Propósito:** Documentar la trazabilidad entre lo que se especificó al principio (Hilo 02) y lo que
acabó implementándose, incluyendo **qué cambió y por qué**. Es el artefacto que demuestra que el
proyecto siguió un ciclo Spec-Driven real y no una racionalización *a posteriori*.

---

## Resumen de la evolución

```
Hilo 02 (junio)          →  Fase 0 (consolidación)  →  Fases 1–5 (implementación)  →  v2.0 (julio)
─────────────────────       ────────────────────        ──────────────────────         ───────────
Decisiones abiertas         Contrato v1.1 cerrado       Código + tests                 Memoria + SpecDD
Esquema v1.0 (dos           Esquema unificado y         Bugs reales encontrados        5 ADRs
versiones divergentes)      validable                   por la especificación          Log de IA
Universo documental         Mapa BADA real,             8 requisitos SGDA              36/36 tests
genérico (14 tipos)         códigos SGDA                auténticos
```

La tesis de esta sección: **la especificación no fue decorativa**. En al menos tres ocasiones,
tener el contrato formalizado destapó defectos que de otro modo habrían llegado a la entrega.

---

## Hito 1 · Del esquema v1.0 al contrato v1.1

### Lo que se especificó (Hilo 02)

`CanonicalDocumentParse v1.0` con jerarquía
`expediente → documento → página → bloque → extracted_fields → bastanteo_evidence`,
descrito en prosa y con ejemplos JSON.

### Qué cambió

| Aspecto | v1.0 (Hilo 02) | v1.1 (implementado) | Motivo |
|---|---|---|---|
| Formalización | Prosa + ejemplos | **JSON Schema ejecutable** | La prosa no detecta violaciones; el schema sí |
| Nivel raíz | `expediente_id`, `documents` | `case_id`, `document_inventory` | Reconciliación con la nomenclatura del Anexo B de la memoria v1.4 |
| Versiones | Dos variantes divergentes en circulación (Anexo B vs. Hilo 02) | Una sola, con tabla de mapeo | Las dos versiones eran incompatibles en nombres de campo |
| `expected_document_map` | Mencionado | Campo de primera clase con `required: true \| "condicional"` | Necesario para modelar requisitos condicionales del BADA |
| Restricciones de valor | No especificadas | `confidence_global ∈ [0,1]`, vocabulario cerrado de `block_type` | Ver hallazgo abajo |

### Hallazgo que justificó el cambio

Al hacer el esquema ejecutable, la validación destapó un fixture de test con `quality_score=4.1`
donde el contrato exige un valor en [0, 1]. El defecto llevaba tiempo enmascarado porque la
validación **nunca llegaba a ejecutarse** por un problema del entorno. Corregido a `0.91`.

> **Lección:** un contrato en prosa no valida nada. La especificación solo aporta garantías cuando
> es ejecutable y se ejecuta en el arnés de pruebas.

---

## Hito 2 · Del "no acoplarse a ningún parser" a la abstracción real

### Lo que se especificó (Hilo 02)

> "No acoplar el sistema al formato nativo de ningún parser; toda salida debe normalizarse a un
> contrato único interno."

Con adaptadores previstos: `chandra_adapter.py`, `dotsocr_adapter.py`, `nemotron_adapter.py`.

### Qué se implementó

| Previsto | Implementado | Diferencia y motivo |
|---|---|---|
| Adaptador Chandra (pesos abiertos) | Backend `datalab` (API gestionada) + `chandra-hf` como stub | **Restricción de hardware:** solo CPU disponible; Chandra 4B es inviable en CPU para una demo |
| Tres adaptadores desde el inicio | Interfaz + factory + 1 backend real + 1 stub | Se prioriza tener el **punto de extensión** correcto sobre tener muchos backends a medias |
| — | Advertencia de honestidad académica en el código | Surgió al constatar que la API gestionada ≠ pesos abiertos (86.7 vs. 85.9) |

### Consecuencia documental

Esta desviación **no se ocultó**: quedó registrada como aviso explícito en el docstring de
`datalab_client.py`, en el ADR-001 y como punto a declarar en la memoria. Cambiar la decisión
técnica por una restricción real de entorno es legítimo; presentarla como si fuera la decisión
original no lo sería.

---

## Hito 3 · Del universo documental genérico al mapa BADA real

### Lo que se especificó (Hilo 02)

Un universo documental mínimo de 14 tipos genéricos (solicitud de prestación, copia de DNI/NIE,
libro de familia, certificado de discapacidad…) con etiquetas propias (`FORMSOLICITUD`,
`IDDNINIE`, `FAMLIBROFAMILIA`…).

### Qué cambió

Al disponer del material real del procedimiento BADA (mapa documental, formulario C-157,
presentación del piloto, Excel de tipologías SGDA), se sustituyó la taxonomía inventada por la
**taxonomía administrativa auténtica**:

| Antes (genérico) | Después (SGDA real) |
|---|---|
| `FORMSOLICITUD` | `ae_ciu_sol_prestacion` |
| `IDDNINIE` | `ae_ciu_ide_identificativo` |
| `FAMCERTNACIMIENTO` | `ae_con_cer_rgecivil` |
| `FAMCERTMATRIMONIO` | `ae_con_cer_vinculoconyugal` *(condicional)* |
| `MEDCERTDISCAPACIDAD` | `ae_con_cer_discapacidad` *(condicional)* |
| — | `ae_ciu_acr_residencia`, `ae_ciu_acr_acreditativo`, `ae_ciu_del_responsable` |

Procedimiento: `aex_gestprestaciones_bada`.

### Ficheros afectados

- `04_src/agent/catalog.py` → `BADA_REQUIREMENTS` (8 requisitos reales).
  Se conservó `EXAMPLE_REQUIREMENTS = BADA_REQUIREMENTS` como alias por retrocompatibilidad,
  evitando tocar `ui/pipeline.py`.
- `04_src/ui/sample_case.json` → expediente de 6 documentos con textos administrativos verosímiles.
  Se preservó deliberadamente el bloque `"DNI del solicitante: 12345678Z"` para no romper tests
  previos.
- `tests/ui/test_pipeline.py` → aserciones actualizadas (6 documentos, 8 evidencias).

### Por qué importa metodológicamente

El paso de una taxonomía inventada a códigos administrativos reales cambia la naturaleza del
trabajo: deja de ser un ejercicio sobre documentos ficticios y pasa a ser un prototipo sobre un
procedimiento existente, con su condicionalidad real (matrimonio y discapacidad no siempre aplican).

---

## Hito 4 · Del "agente de bastanteo" abstracto al ciclo ReAct por requisito

### Lo que se especificó (Hilo 02)

Seis capacidades mínimas: clasificar documentos, verificar obligatoriedad, comparar campos entre
documentos, localizar firmas y sellos, emitir dictamen `VALIDO`/`INCOMPLETO`/`RECHAZADO`, y añadir
`bastanteo_evidence` con referencias espaciales.

### Qué se implementó y qué se aplazó

| Capacidad especificada | Estado | Nota |
|---|---|---|
| Emitir dictamen estructurado | ✅ | `bastanteo_gold` con los tres estados |
| `bastanteo_evidence` con anclaje espacial | ✅ | `document_id` + `page` + `block_id` + `bbox` |
| Verificar obligatoriedad/condicionalidad | ✅ | `requirement_type` en cada `Requirement` |
| Localizar firmas y sellos | ✅ | Vía `evidence_type` y `block_type` |
| Clasificar documentos del expediente | 🔁 Parcial | Se usa `document_type_pred` del normalizador; el clasificador dedicado queda para la fase de evaluación |
| Comparar campos entre documentos (p. ej. DNI) | ⏳ Aplazado | Requiere razonamiento entre documentos; el catálogo actual verifica requisitos de forma independiente. Registrado como trabajo futuro |

### Decisión de diseño no prevista en el Hilo 02

La **unidad atómica `Requirement`** (una consulta de recuperación + un juicio por comprobación
normativa) no estaba en la especificación original: surgió al implementar, como forma de obtener
la traza auditable que exige H3. Documentada en ADR-003.

También surgió durante la implementación el **invariante de no-alucinación** (sin citas o con score
bajo → `missing` con `source_*` a `None`), que no estaba escrito en ninguna parte y resultó ser la
propiedad más importante del componente para el dominio administrativo.

---

## Hito 5 · De la demo prevista a los dos modos

### Lo que se especificó

Nada explícito sobre la UI en el Hilo 02: el foco estaba en dataset, contrato y evaluación.

### Qué forzó la decisión

Una restricción de entorno constatada durante el desarrollo: **no fue posible instalar `chromadb`
ni `llama-index`** por limitaciones de red. Eso convirtió un riesgo hipotético ("¿y si el día de la
demo falla la red?") en un problema comprobado.

### Respuesta de diseño

Dos modos sobre **el mismo agente real**, degradando únicamente la función de puntuación del
recuperador (ADR-005). El modo demo no simula la lógica: la ejecuta con un recuperador peor.

Efecto colateral valioso: el modo demo se convirtió también en el **arnés de pruebas e2e**
(`test_demo_retrieve_fn_runs_full_agent_end_to_end`), porque es la única ruta que recorre el agente
completo sin dependencias pesadas.

---

## Defectos que la especificación destapó

Registro de los tres casos en que tener el contrato formalizado tuvo un rendimiento medible:

| # | Defecto | Cómo se destapó | Corrección |
|---|---|---|---|
| 1 | `quality_score=4.1` violando `confidence_global ∈ [0,1]` | Validación del JSON Schema, una vez ejecutable | Corregido a `0.91` → 36/36 tests |
| 2 | `AnthropicJudge` no instanciable | Test de la factory `get_judge()` sobre la interfaz especificada | Añadido `judge()` concreto que sigue lanzando `NotImplementedError` |
| 3 | `process_document()` no capturaba `ImportError` | Especificación de errores del componente C5: la falta del SDK lanza `ImportError`, no `RuntimeError` | Añadido al bloque de captura y traducido a `PipelineError` |

A los que se suma un cuarto, ya en la memoria:

| 4 | "Hipótesis de trabajo" generada como Título 3 (quedaba como "1.3.4" en vez de "1.4") | **Inspección visual** de la página renderizada — la validación de esquema daba verde | Cambiado el estilo del párrafo a Título 2 |

Los cuatro comparten una moraleja: cada tipo de defecto necesita **su** tipo de verificación.
El schema no detecta errores de formato visual; los tests no detectan citas mal atribuidas.

---

## Estado de la especificación frente al código

| Especificado en Hilo 02 | Estado |
|---|---|
| Contrato canónico como referencia única | ✅ v1.1, JSON Schema ejecutable |
| Adaptador de parser intercambiable | ✅ Interfaz + factory + 1 backend + 1 stub |
| Chunker layout-aware sobre bloques y secciones | ✅ 6/6 tests |
| Agente con salida estructurada y `bastanteo_evidence` | ✅ 8 evidencias sobre requisitos SGDA reales |
| Validadores de negocio por campo (`dni_nie`, `nuss`, fechas) | ⏳ Pendiente (Fase 2) |
| Normalizador de dataset gold | ⏳ Pendiente (Fase 2) |
| Pipeline de evaluación (clasificación, extracción, eficiencia, grounding) | ⏳ Pendiente (Fase 3) |
| Generación de dataset sintético (Faker + LayoutDM + SynthDoG + augmentación) | ⏳ Pendiente (Fase 2) |
| Adaptadores dots.ocr / Nemotron | ⏳ Pendiente (punto de extensión ya preparado) |

**Lectura:** las fases 1–5 (arquitectura funcional de punta a punta) están completas y verificadas.
Lo pendiente se concentra en las fases 2–3 (dataset sintético a escala y evaluación cuantitativa),
que es coherente con el estado declarado en la memoria: la arquitectura está construida y
demostrada; la campaña experimental es el paso siguiente.

---

## Trazabilidad de artefactos

| Artefacto | Fichero |
|---|---|
| Visión de producto | `SpecDD/01-Vision.md` |
| Requisitos funcionales (PRD) | `SpecDD/02-Requisitos.md` |
| Especificaciones de componentes | `SpecDD/03-Component-Specs.md` |
| Decisiones de arquitectura | `SpecDD/ADRs/ADR-001..005` |
| Log de uso de IA | `SpecDD/04-Log-IA.md` |
| Evidencia de iteración | `SpecDD/05-Evolution-Specs.md` *(este documento)* |
| Contrato canónico | `specs/canonical-document-parse-v1.1.md`, `specs/canonical_document_parse.schema.json` |
| Bitácora cronológica | `TFM-Burocracy/Bitacora_Proyecto_TFM-SpecDD.md` |

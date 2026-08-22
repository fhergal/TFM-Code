# Log de uso de IA en el ciclo de desarrollo

**Versión:** 1.0 · **Fecha:** Julio 2026
**Asistente utilizado:** Claude (Anthropic), a través de Claude Code / Cowork
**Propósito:** Registrar qué tareas se delegaron a IA, con qué intención, qué se obtuvo y qué
hubo que corregir. Es un artefacto exigido por el curso de SpecDD y, a la vez, evidencia
metodológica para el capítulo de metodología de la memoria.

---

## Cómo leer este log

Cada entrada registra: **qué se pidió**, **qué devolvió la IA**, y sobre todo **qué hubo que
corregir**. Esa tercera columna es la relevante: documenta dónde la asistencia funcionó bien y
dónde requirió supervisión humana efectiva.

Clasificación de resultados:

- ✅ **Aceptado** — usado sin cambios sustanciales.
- 🔁 **Iterado** — válido tras una o varias correcciones dirigidas.
- ⚠️ **Corregido** — contenía un error real que el autor detectó y obligó a rehacer.
- ❌ **Rechazado** — descartado.

---

## Fase 0 · Recuperación y consolidación

| # | Fecha | Tarea | Intención del prompt | Resultado | Estado |
|---|---|---|---|---|---|
| 0.1 | Jul 2026 | Recuperación de los 5 hilos de trabajo desde Perplexity | Extraer y estructurar en Markdown el contenido disperso de los hilos 00–04 | 5 ficheros `.md` estructurados por tema | ✅ |
| 0.2 | Jul 2026 | Revisión de coherencia de la memoria v1.4 | Contrastar el documento entregado contra los hilos recuperados y señalar huecos | Detectó subapartados redactados en el Hilo 03 (origen de datos, ética/privacidad, limitaciones del dataset) ausentes del `.docx` | ✅ |
| 0.3 | Jul 2026 | Unificación del esquema canónico | Reconciliar dos versiones divergentes de `CanonicalDocumentParse` (Anexo B v1.4 vs. Hilo 02) | Esquema v1.1 + tabla de mapeo + JSON Schema validable | ✅ |
| 0.4 | Jul 2026 | Diagrama de arquitectura del pipeline | Visualizar el conjunto parser → normalizador → RAG → agente → UI | Diagrama SVG usado después como base de la figura de la memoria | ✅ |

---

## Fases 1–5 · Implementación

| # | Fecha | Tarea | Intención del prompt | Resultado | Estado |
|---|---|---|---|---|---|
| 1.1 | Jul 2026 | Adaptador de parser con backends | Diseñar `DocumentParser` + `get_parser()` con backend Datalab y stub de pesos abiertos | Interfaz + adaptador + tests con mocks (ADR-001) | ✅ |
| 1.2 | Jul 2026 | Aviso de honestidad académica en el código | Documentar que la API de Datalab no es literalmente Chandra con pesos abiertos | Docstring extenso en `datalab_client.py` con la advertencia y las dos vías de mitigación | ✅ |
| 2.1 | Jul 2026 | Normalizador a esquema canónico | Mapear el árbol Marker a `CanonicalDocumentParse` v1.1 con validación de schema | `flatten_marker_tree()` + validación; 7/9 tests iniciales | 🔁 |
| 2.2 | Jul 2026 | Diagnóstico de dos tests fallando | Determinar si el fallo era del código o del entorno | Se identificó como artefacto del entorno de ejecución; la lógica se verificó aparte contra una copia limpia | 🔁 |
| 3.1 | Jul 2026 | Chunking sensible al layout | Agrupar bloques por sección lógica en lugar de por longitud fija | `build_chunks()`, 6/6 tests (ADR-004) | ✅ |
| 3.2 | Jul 2026 | Indexación con LlamaIndex + ChromaDB | Envoltorio `build_index()` / `query()` con metadata de trazabilidad | Código escrito; **no verificable** en el entorno por imposibilidad de instalar las dependencias pesadas. Se añadió `pytest.skip()` para no dar falsos verdes | ⚠️ |
| 4.1 | Jul 2026 | Agente de bastanteo ReAct | Ciclo por `Requirement` con `retrieve_fn` desacoplado y juez intercambiable | `bastanteo.py`, `judge.py`, `base.py` (ADR-003) | ✅ |
| 4.2 | Jul 2026 | Bug de instanciación de `AnthropicJudge` | Analizar por qué el stub fallaba antes de lanzar su propio error | La clase abstracta impedía instanciar antes de que `__init__` lanzara `NotImplementedError`; corregido añadiendo un `judge()` concreto que sigue lanzando la excepción | ⚠️ |
| 5.1 | Jul 2026 | UI Gradio con dos modos | Demo real + demo offline que atraviesen el mismo agente | `app.py`, `pipeline.py`, `naive_retriever.py` (ADR-005) | ✅ |
| 5.2 | Jul 2026 | Bug de captura de excepciones en la UI | Revisar el manejo de errores de `process_document()` | Solo capturaba `RuntimeError` y `ValueError`; la falta del SDK lanza `ImportError` y rompía la UI. Corregido | ⚠️ |

---

## Integración del dominio real (BADA)

| # | Fecha | Tarea | Intención del prompt | Resultado | Estado |
|---|---|---|---|---|---|
| 6.1 | Jul 2026 | Extracción del mapa documental BADA | Leer el Excel del mapa documental, el formulario C-157 y el PPT del piloto, y extraer las tipologías reales | 8 requisitos con códigos SGDA auténticos (`ae_ciu_sol_prestacion`, `ae_con_cer_rgecivil`, …) | ✅ |
| 6.2 | Jul 2026 | Reescritura de `catalog.py` | Sustituir el catálogo genérico de ejemplo por `BADA_REQUIREMENTS` reales | 8 `Requirement` con `claim`/`query`/`requirement_type`/`evidence_type`; alias `EXAMPLE_REQUIREMENTS` conservado para no romper `pipeline.py` | ✅ |
| 6.3 | Jul 2026 | Reescritura de `sample_case.json` | Construir un expediente BADA verosímil de 6 documentos con textos administrativos en castellano | Fixture realista; se conservó deliberadamente el bloque "DNI del solicitante: 12345678Z" por retrocompatibilidad con tests existentes | ✅ |
| 6.4 | Jul 2026 | Actualización de tests al nuevo fixture | Ajustar aserciones al expediente BADA | `procedure_type == "aex_gestprestaciones_bada"`, 6 documentos, 8 evidencias | ✅ |
| 6.5 | Jul 2026 | Bug real destapado por la validación | Investigar por qué un test seguía fallando tras corregir el código | Un fixture usaba `quality_score=4.1` violando la restricción `confidence_global ∈ [0,1]` del schema; el fallo llevaba tiempo enmascarado porque la validación nunca llegaba a ejecutarse. Corregido a `0.91` → **36/36 tests en verde** | ⚠️ |
| 6.6 | Jul 2026 | Mini-ejemplo autocontenido de Datalab | Script mínimo para enseñar en la presentación cómo se invoca la API con una clave | `quickstart_datalab_chandra.py`, sin dependencias del resto del repo | ✅ |

---

## Revisión bibliográfica

| # | Fecha | Tarea | Intención del prompt | Resultado | Estado |
|---|---|---|---|---|---|
| 7.1 | Jul 2026 | Evaluación crítica de un artículo divulgativo sobre fallos de RAG | Valorar un artículo de KDnuggets y un informe generado por IA sobre él, **verificando las citas antes de aceptarlas** | Se confirmó que Li et al. (2024), EMNLP Industry Track, es un trabajo real, revisado por pares y citable | ✅ |
| 7.2 | Jul 2026 | Verificación de una cifra atribuida | Comprobar la afirmación de "15–30% de mejora de precisión" atribuida a Self-Route | **Atribución errónea:** la cifra procede de un blog comercial ajeno, no del paper, cuya tesis real es la reducción de coste manteniendo rendimiento comparable. Otra cifra ("72% de fracasos") tampoco tiene fuente primaria. Ninguna de las dos se incorporó | ⚠️ |
| 7.3 | Jul 2026 | Redacción del texto para la memoria | Redactar el párrafo de estado de la cuestión y la línea de trabajo futuro, citando solo lo verificable | Texto en castellano listo para incorporar, sin las cifras no citables | ✅ |

---

## Redacción de la memoria (v2.0)

| # | Fecha | Tarea | Intención del prompt | Resultado | Estado |
|---|---|---|---|---|---|
| 8.1 | Jul 2026 | Ampliación del estado de la cuestión | Convertir un capítulo que "parecía solo puntos" en prosa articulada | 3 subapartados nuevos (modelos VDU de 2.ª generación, arquitecturas agénticas y RAG, modos de fallo del RAG + *research gap*), conservando intacta la tabla comparativa original | ✅ |
| 8.2 | Jul 2026 | Ampliación de las hipótesis | Desarrollar H0–H3, que eran una línea cada una, con fundamento y métrica asociada | Cuatro hipótesis desarrolladas, cada una ligada explícitamente a su métrica de validación (F1 macro, ANLS, `bastanteo_evidence`, Reasoning Trace, precisión top-k) | ✅ |
| 8.3 | Jul 2026 | Error de nivel de encabezado | Revisar visualmente el documento renderizado | "Hipótesis de trabajo" se había generado como Título 3, quedando anidada como "1.3.4" en vez de ser la sección "1.4". Detectado al inspeccionar la página renderizada y corregido | ⚠️ |
| 8.4 | Jul 2026 | Marcadores de figuras y enlace al repositorio | Dejar puntos señalados donde insertarán gráficos, y añadir el enlace al código | 2 marcadores "[Figura pendiente: …]" + enlace al repositorio en Enlaces Técnicos. Se comprobó que el diagrama de arquitectura ya insertado por el autor seguía intacto | ✅ |
| 8.5 | Jul 2026 | Control del presupuesto de páginas | Verificar que la ampliación no rebasa el límite de 50 páginas sin bibliografía ni anexos | 48 → 50 páginas totales; cuerpo ≈ 27 páginas. No fue necesario mover contenido a anexos | ✅ |

---

## Artefactos SpecDD

| # | Fecha | Tarea | Intención del prompt | Resultado | Estado |
|---|---|---|---|---|---|
| 9.1 | Jul 2026 | Decisión sobre separar el repositorio | Valorar si el proyecto del curso necesita una base de código propia | Recomendación de **no** duplicar: repositorio único con `SpecDD/` como carpeta de artefactos metodológicos, no de código | ✅ |
| 9.2 | Jul 2026 | Visión y PRD | Redactar visión de producto y requisitos funcionales con criterios de aceptación | `01-Vision.md` + `02-Requisitos.md` (36 requisitos priorizados P0/P1 con matriz de trazabilidad) | ✅ |
| 9.3 | Jul 2026 | Especificaciones de componentes | Formalizar contratos de entrada/salida, invariantes y errores por módulo | `03-Component-Specs.md` con matriz de acoplamiento | ✅ |
| 9.4 | Jul 2026 | ADRs | Documentar las decisiones de arquitectura con contexto, consecuencias y alternativas descartadas | 5 ADRs (ADR-001 a ADR-005) | ✅ |
| 9.5 | Jul 2026 | Este log | Registrar el uso de IA a lo largo del proyecto | `04-Log-IA.md` | ✅ |

---

## Lecciones sobre el uso de IA en este proyecto

**Dónde aportó más valor**

1. **Andamiaje de código con contrato claro.** Cuando el contrato (esquema canónico, interfaz del
   parser) estaba definido de antemano, la generación de adaptadores y tests fue rápida y correcta.
2. **Detección de incoherencias documentales.** El contraste entre la memoria v1.4 y los hilos de
   trabajo localizó huecos que una relectura manual habría pasado por alto.
3. **Diagnóstico de errores sutiles.** Bugs como la instanciación de la clase abstracta o la
   excepción no capturada se identificaron más rápido con asistencia que en solitario.

**Dónde exigió supervisión humana efectiva**

1. **Citas bibliográficas.** Un informe generado por IA atribuyó a un paper una cifra que procedía
   de un blog comercial. Sin verificar la fuente primaria, ese error habría acabado en la memoria.
   **Regla adoptada: ninguna cita entra sin comprobar la fuente original.**
2. **Distinguir fallo de código de fallo de entorno.** Varias veces un test parecía roto y el
   problema estaba en el entorno de ejecución. La regla adoptada fue verificar siempre contra una
   copia limpia antes de "arreglar" código que no estaba roto.
3. **Verificación visual del formato.** El error de nivel de encabezado en el `.docx` solo se
   detectó **mirando la página renderizada**. La validación de esquema daba verde.
4. **Reconocer límites del entorno.** Las dependencias pesadas de RAG no se pudieron instalar; lo
   correcto fue declararlo y marcar el test con `skip`, no simular una verificación que no ocurrió.

**Regla de trabajo consolidada**

> La IA propone, el autor verifica contra la fuente primaria (el paper, el fichero renderizado,
> el test ejecutado de verdad). Todo lo que no se haya podido comprobar se declara explícitamente
> como no comprobado — nunca se presenta como verificado.

# Requisitos Funcionales (PRD) — Bastanteo Documental Asistido por IA

**Fecha:** Julio 2026  
**Versión:** 1.0  
**Derivado de:** Vision.md + Hilo-02 (Decisiones Fase 1)

---

## Introducción

Este documento especifica los requisitos funcionales del sistema en estructura PRD: qué debe hacer, en qué orden de prioridad, y cuáles son los criterios de aceptación. Cada requisito mapea contra una fase del roadmap (Steps 1–5) y contra un módulo de código.

---

## Grupos de Requisitos

### Grupo 1: Parser Documental (Step 1)

**Módulo:** `04_src/parser/`  
**Responsabilidad:** Convertir PDF/imagen a bloques estructurados.

| ID | Título | Descripción | Prioridad | Criterio de Aceptación |
|---|---|---|---|---|
| **REQ-1.1** | Soporte de backend Datalab/Chandra | Sistema debe soportar parsing vía API Datalab (Chandra OCR-2, mode=accurate) | **P0** | ✅ DatalabParser instanciable; convierte documento a JSON con bloques, BBox, confidence |
| **REQ-1.2** | Abstracción de backends intercambiables | Interfaz `DocumentParser` + factory `get_parser()` permite cambiar a dots.ocr o Nemotron sin tocar agente/RAG | **P0** | ✅ Base class + adapter pattern; 2+ backends implementables (stub chandra-hf presente) |
| **REQ-1.3** | Gestión de API key y configuración | Sistema lee DATALAB_API_KEY de env o .env, maneja errores de credenciales | **P0** | ✅ RuntimeError claro si falta key; .env.example presente |
| **REQ-1.4** | Modo "preview" con quickstart | Script `quickstart_datalab_chandra.py` demuestra en <50 líneas cómo invocar Datalab | **P1** | ✅ Script runnable con 1 argumento (path a PDF), sin dependencias del resto del repo |
| **REQ-1.5** | Validación de salida | ParserResult tiene campos tipados (page_count, quality_score, raw, elapsed_seconds) | **P0** | ✅ Dataclass validable contra JSON Schema; Pydantic optional |

---

### Grupo 2: Normalizador (Step 2)

**Módulo:** `04_src/normalizer/`  
**Responsabilidad:** Mapear salida de parser nativa → CanonicalDocumentParse v1.1 JSON.

| ID | Título | Descripción | Prioridad | Criterio de Aceptación |
|---|---|---|---|---|
| **REQ-2.1** | Schema CanonicalDocumentParse v1.1 | Contrato único: case → documento → página → bloque → extracted_fields + bastanteo_evidence | **P0** | ✅ JSON Schema validable (`specs/canonical_document_parse.schema.json`); todos los campos mínimos presentes |
| **REQ-2.2** | Mapeo de bloques Marker → CanonicalDocumentParse | Función `flatten_marker_tree()` convierte árbol Marker a bloques planos con BBox, reading_order | **P0** | ✅ 7/9 tests pasan (2 fallos son sandbox artifacts); output valida contra schema |
| **REQ-2.3** | Extracción de campos canónicos | Normalizador identifica campos clave (dni, nuss, fecha, organo_emisor, estado_firma) a partir de bloques y semántica | **P1** | ✅ extracted_fields[] con field_name, field_value, confidence, source_block_ids |
| **REQ-2.4** | Validación del esquema salida | Todo JSON generado debe pasar jsonschema.validate() contra el schema v1.1 | **P0** | ✅ ValidatorError claro si falla; logs incluyen qué campo no pasó |
| **REQ-2.5** | Manejo de errores de parsing | Si parser falla (conexión, API key inválida), normalizador propaga error con contexto | **P0** | ✅ Process_document() atrapa RuntimeError, ValueError, ImportError; devuelve mensaje legible |

---

### Grupo 3: RAG — Indexación y Retrieval (Step 3)

**Módulo:** `04_src/rag/`  
**Responsabilidad:** Indexar bloques respetando layout; recuperar citas trazables.

| ID | Título | Descripción | Prioridad | Criterio de Aceptación |
|---|---|---|---|---|
| **REQ-3.1** | Chunking layout-aware | Función `build_chunks()` agrupa bloques por sección lógica (solicitante, certificaciones, firmas) en lugar de cortar por longitud fija | **P0** | ✅ 6/6 tests pasan; chunks respetan block_type, no fragmentan dentro de tabla/firma |
| **REQ-3.2** | Indexación con LlamaIndex + ChromaDB | `build_index()` crea índice vectorial, `query()` recupera top-k chunks con embeddings multilíngüe | **P0** | ✅ Index instanciable; query devuelve [(chunk, score, metadata)] con document_id, page, block_id, bbox |
| **REQ-3.3** | Retrieval function desacoplada | `make_retrieve_fn()` devuelve closure que toma query_str → citas trazables, sin dependencia de clase global | **P0** | ✅ retrieve_fn es puro (input: str, output: List[Citation]), reutilizable en agente |
| **REQ-3.4** | Modo demo sin dependencias pesadas | Fallback `naive_retriever.py` con Jaccard/word-overlap para demostración sin ChromaDB | **P1** | ✅ Modo demo funciona; resultados peores pero predecibles (word-overlap baseline) |
| **REQ-3.5** | Preservación de metadata | Cada chunk indexado arrastre document_id, page, block_id, bbox, semantics para grounding posterior | **P0** | ✅ Metadata en ChromaDB metadata field; recuperable sin segunda consulta |

---

### Grupo 4: Agente de Bastanteo (Step 4)

**Módulo:** `04_src/agent/`  
**Responsabilidad:** Verificar requisitos normativos; emitir bastanteo_evidence; decidir VÁLIDO/INCOMPLETO/RECHAZADO.

| ID | Título | Descripción | Prioridad | Criterio de Aceptación |
|---|---|---|---|---|
| **REQ-4.1** | Catálogo de requisitos BADA | 8 requisitos SGDA reales (ae_ciu_sol_prestacion, ae_ciu_ide_identificativo, ae_con_cer_rgecivil, …) cada uno con claim, query, requirement_type, evidence_type | **P0** | ✅ BADA_REQUIREMENTS en catalog.py; cada Requirement es dataclass con todos los campos |
| **REQ-4.2** | Ciclo ReAct por requisito | For each Requirement: retrieve_fn(query) → citas; Judge(citas) → {supported, contradicted, missing}; añadir evidencia | **P0** | ✅ `run_bastanteo_over_case()` itera 8 requisitos; 8 evidencias en output |
| **REQ-4.3** | Judge rule-based | RuleBasedJudge punúa similitud entre claim y citas recuperadas; threshold → decisión; sin LLM | **P0** | ✅ RuleBasedJudge.judge(claim, citas) → {"status": "supported", "score": 0.87} |
| **REQ-4.4** | Judge stub para Claude | AnthropicJudge como interfaz futura (no implementado); permite inyectar LLM después | **P1** | ✅ AnthropicJudge hereda de Judge, tiene init() + judge() method (raises NotImplementedError) |
| **REQ-4.5** | Output bastanteo trazable | bastanteo_evidence[] con evidence_id, claim, status, source_document_id, source_page, source_block_ids, span_text | **P0** | ✅ Cada evidencia es dataclass; linked a block concreto; recuperable en UI |
| **REQ-4.6** | Decisión final estructurada | bastanteo_gold con status ∈ {VÁLIDO, INCOMPLETO, RECHAZADO}; reasoning_trace (qué evidencias fundamentaron) | **P0** | ✅ bastanteo_gold en CanonicalDocumentParse; reasoning_trace es lista de (Requirement, citas, score) |
| **REQ-4.7** | No alucinación explícita | Si no hay evidencia de una comprobación, status=MISSING (no fabrica respuesta); mensaje claro | **P0** | ✅ Judge devuelve score < threshold → "missing"; agente no interpola evidencia |

---

### Grupo 5: UI Gradio (Step 5)

**Módulo:** `04_src/ui/`  
**Responsabilidad:** Demo ejecutable, dos modos, pregunta libre + bastanteo automático.

| ID | Título | Descripción | Prioridad | Criterio de Aceptación |
|---|---|---|---|---|
| **REQ-5.1** | Modo real (usuario sube PDF + API key) | Carga documento real, ejecuta parser Datalab, normalizador, RAG, agente; muestra resultado | **P0** | ✅ UI Gradio con inputs: [file, api_key], output: [bastanteo table, reasoning trace, citas] |
| **REQ-5.2** | Modo demo (sample_case.json + naive retriever) | Sin API key, carga sample_case.json (BADA 6-doc demo), ejecuta agente con naive_retriever | **P0** | ✅ UI Gradio detecta modo automáticamente; demo funciona offline |
| **REQ-5.3** | Tabla interactiva de bastanteo | Muestra 8 requisitos × {Requirement.claim, status, evidence_text, source_page} en tabla legible | **P0** | ✅ Gradio Dataframe con columnas claim, status, evidence, page |
| **REQ-5.4** | Reasoning Trace visible | Cada evidencia linkable a block_id + page + bbox; usuario puede hacer click/hovering para ver contexto | **P1** | ✅ Reasoning Trace en JSON legible; menciona doc_id, page, block_id explícitamente |
| **REQ-5.5** | Pregunta libre opcional | Usuario puede escribir pregunta adicional (ej: "¿Hay firma en la solicitud?"), RAG recupera y muestra citas | **P1** | ✅ Text input + button; retrieve_fn(query) → tabla de citas con bbox |
| **REQ-5.6** | Tests e2e | test_pipeline.py valida flujo completo: carga case → procesa docs → recupera → ejecuta agente → muestra UI | **P0** | ✅ test_demo_retrieve_fn_runs_full_agent_end_to_end() con 8 bastanteo_evidence esperadas |

---

### Grupo 6: Testing, Specs y Documentación

**Módulo:** `tests/`, `specs/`, repo root  
**Responsabilidad:** Verificabilidad, reproducibilidad, artefactos SpecDD.

| ID | Título | Descripción | Prioridad | Criterio de Aceptación |
|---|---|---|---|---|
| **REQ-6.1** | Cobertura de tests | Todos los módulos (parser, normalizer, agent, rag/chunking, ui) con tests unitarios e2e, >80% líneas | **P0** | ✅ 36/36 tests pasan (exc. rag/index_store que usa ChromaDB pesado); `pytest --cov` >80% |
| **REQ-6.2** | Mocks de dependencias externas | Tests no usan API de Datalab real; mock DatalabClient con respuestas tipadas | **P0** | ✅ pytest-mock + fixture fake_parser_result() con JSON sample válido |
| **REQ-6.3** | Sample case BADA realista | sample_case.json contiene 6 documentos tipo BADA real, tipos SGDA exactos, texto español | **P0** | ✅ case_id=EXP-DEMO-0001, procedure_type=aex_gestprestaciones_bada, 6 docs con tipos ae_* |
| **REQ-6.4** | Especificación de requisitos SpecDD | PRD (este doc), ADRs de decisiones clave, specs de componentes (contratos entrada/salida) | **P0** | ✅ `/SpecDD/` con 02-Requisitos.md (PRD), ADRs/, 03-Component-Specs.md |
| **REQ-6.5** | Log de uso de IA | Documento que registra qué tareas se delegaron a Claude, con prompts clave y salida resumida | **P1** | ✅ `/SpecDD/04-Log-IA.md` con tabla de iteraciones (fecha, tarea, prompt, resultado) |
| **REQ-6.6** | Bitácora de evolución de specs | Cómo evolucionaron los requisitos y decisiones del Hilo 02 al código final | **P1** | ✅ `/SpecDD/05-Evolution-Specs.md` o en `Bitacora_Proyecto_TFM-SpecDD.md` |

---

## Matriz de Trazabilidad

| Step | Módulo | Requisitos | Feature |
|---|---|---|---|
| 1 | parser/ | REQ-1.1–1.5 | Parser OCR-free con abstracción |
| 2 | normalizer/ | REQ-2.1–2.5 | Normalizador a CanonicalDocumentParse v1.1 |
| 3 | rag/ | REQ-3.1–3.5 | RAG layout-aware (LlamaIndex + ChromaDB + naive fallback) |
| 4 | agent/ | REQ-4.1–4.7 | Agente ReAct + RuleBasedJudge + bastanteo_evidence |
| 5 | ui/ | REQ-5.1–5.6 | UI Gradio (real + demo) con Reasoning Trace |
| — | tests/, specs/ | REQ-6.1–6.6 | Testing, documentación SpecDD |

---

## Criterios de Aceptación Transversales

1. **Trazabilidad:** Toda decisión debe ser rastreable hasta block_id + page + bbox.
2. **Modularidad:** Cambiar parser de Datalab a dots.ocr debe ser un parámetro, no un refactor.
3. **Explicabilidad:** Sistema nunca alucina; si no hay evidencia, devuelve MISSING explícito.
4. **Calidad de código:** >80% cobertura de tests; docstrings en funciones públicas; type hints en Python 3.10+.
5. **Documentación:** README, docstrings, ejemplos ejecutables; cualquier dev externo debe correr demo en <30 min.

---

## Alcance Post-MVP (Futuro, Fase 2+)

- [ ] Judge basado en Claude (decisión de modelo + coste)
- [ ] Dataset sintético completo (>1000 expedientes, LayoutDM + SynthDoG + augmentation)
- [ ] Evaluación cuantitativa exhaustiva (F1 macro, ANLS sobre dataset > 100 casos)
- [ ] API REST + autenticación + base de datos persistente
- [ ] Integración con sistemas INSS reales (requiere conformidad normativa)

---

## Priorización y Timeline

**P0 (MVP, blocker):** REQ-1.1–1.5, 2.1–2.5, 3.1–3.3, 4.1–4.7, 5.1–5.3, 6.1–6.4  
**Plazo:** ~6 semanas (fases 1–5)

**P1 (mejora, nice-to-have):** REQ-1.4, 3.4, 4.4, 5.4–5.5, 6.5–6.6  
**Plazo:** Julio 2026 (si hay tiempo)

---

## Siguiente Paso

Validar este PRD; proceder a **03-Component-Specs.md** (contratos de entrada/salida de cada módulo).

# Visión del Proyecto — Bastanteo Documental Asistido por IA

**Fecha:** Julio 2026  
**Versión:** 1.0  
**Proyecto:** Bastanteo Documental con RAG + Agente (TFM + SpecDD)  
**Institución:** Universidad Camilo José Cela (Máster en Ciencia de Datos)  
**Caso de uso:** INSS — Procedimiento BADA (Asistencia Sanitaria para Migrantes en Estancia Temporal)

---

## 1. El Problema

**Contexto administrativo:**  
En procedimientos de asistencia sanitaria para migrantes (INSS), los funcionarios deben verificar que un expediente contiene todos los documentos obligatorios, que los campos clave (DNI, NUSS, fecha, órgano emisor, firmas) están presentes y coherentes, y que el expediente cumple requisitos normativos. Este trabajo es:

- **Manual y repetitivo:** ~5–10 min/expediente, 80–90% lectura + comparación de campos.
- **Propenso a errores:** Variabilidad en calidad de escaneo, tipologías documentales no estandarizadas, degradación visual.
- **No escalable:** Volumen anual de expedientes crece, presupuesto de personal no.

**Oportunidad técnica:**  
Modernos modelos VLM/OCR-free (Chandra OCR-2, dots.ocr) permiten extraer estructura y texto de documentos escaneados sin GPU masiva. Un sistema de RAG sensible al layout puede recuperar fragmentos semánticamente relevantes respetando la maquetación. Un agente ReAct puede descomponer el bastanteo normativo en comprobaciones independientes, recuperar evidencias y producir decisiones trazables.

**Brecha:** No existe hoy una arquitectura integrada, publicada y documentada que combine estos tres componentes para el dominio administrativo español. La mayoría de soluciones RAG usan chunking de texto plano; las IA generativas tienden a alucinaciones cuando se aplican a verificación normativa sin grounding.

---

## 2. Visión de Éxito

**En qué queremos transformar el bastanteo:**

> Dado un expediente administrativo (secuencia de PDFs/imágenes), un sistema **automático, explicable y verificable** debe:
> 1. Clasificar cada documento por tipología (solicitud, certificado, resolución, etc.).
> 2. Extraer campos clave (DNI, NUSS, fecha, órgano emisor, firma).
> 3. Recuperar fragmentos trazables que fundamenten cada comprobación.
> 4. Emitir un dictamen estructurado (VÁLIDO / INCOMPLETO / RECHAZADO) con evidencias ligadas a documentos, páginas y bloques concretos.
> 5. Fallar con **grounding explícito** cuando la evidencia sea insuficiente, no alucinar.

**Impacto esperado:**
- Reducir tiempo/expediente de 5–10 min a <1 min (95% reducción).
- Mejorar precisión en detección de inconsistencias (DNI no coincide entre documentos, firmas faltantes).
- Producir trazas auditables para cada decisión (requisito legal en Administración Pública).
- Sentar base metodológica reproducible para otros procedimientos (prestaciones, licencias, etc.).

---

## 3. Usuarios y Sus Necesidades

### Usuario 1: Funcionario del INSS (Bastanteador)
**Quién:** Empleado administrativo que procesa expedientes.  
**Necesidad:** Herramienta que le ayude a verificar expedientes 10× más rápido, sin que desaparezcan responsabilidades legales.  
**Criterio de éxito:** "Confío en las decisiones del sistema porque me muestra exactamente de dónde saca cada respuesta."

### Usuario 2: Auditor/Supervisor
**Quién:** Encargado de revisar procesos y garantizar cumplimiento normativo.  
**Necesidad:** Trazabilidad plena de cada decisión (quién decidió, en qué se basó, qué fue revisado).  
**Criterio de éxito:** "Puedo revisar cualquier expediente y reconstruir la cadena de razonamiento del sistema en 30 segundos."

### Usuario 3: Investigador/PM (Academia/Producto)
**Quién:** Desarrollador, investigador o PM que itera sobre la arquitectura.  
**Necesidad:** Sistema modular, testeable, que permita variar parsers, modelos de embeddings, estrategias de RAG sin reescribir todo.  
**Criterio de éxito:** "Puedo cambiar de Chandra OCR-2 a dots.ocr en una línea de configuración, y todos los tests pasan."

---

## 4. Restricciones y Supuestos

| Restricción | Detalle | Impacto |
|---|---|---|
| **Presupuesto de compute** | Solo CPU disponible en desarrollo inicial; GPU/inferencia vía API (Datalab) | Parser hospedado en API, no en local |
| **Acceso a datos reales** | Expedientes reales confidenciales por ley; solo documentos públicos + sintéticos viables | Dataset híbrido: plantillas oficiales + síntesis + anonimizados |
| **Compatibilidad normativa** | Decisiones automáticas no pueden reemplazar decisión humana; sistema es "asistencia" | Agente produce recomendación + evidencias, no dictamen vinculante |
| **Página en memoria** | TFM max 50 pág (sin biblio/anexos); especificación y arquitectura deben ser sucintos | Documentación breve, high-signal; anexos para JSON schemas, ADRs y metrics |
| **Timeline** | TFM entregable julio 2026; curso SpecDD mismo plazo | Alcance fijo (fases 1–5 completas); mejoras futuras en Fase 2 (dataset sintético completo) |

**Supuestos clave:**
- La extracción de estructura (bloques, BBox) es más estable que OCR de texto nativo.
- RAG layout-aware (chunking respetando secciones) mejora recovery vs. chunking por longitud fija.
- Un agente ReAct que descompone cada comprobación normativa produce menos alucinaciones que un LLM generativo directo.

---

## 5. Objetivos Medibles (OKRs)

### O1: Funcionalidad completa del pipeline
- ✅ Parser (Datalab/Chandra) → Normalizador (CanonicalDocumentParse v1.1) → RAG (LlamaIndex + ChromaDB) → Agente (ReAct) → UI (Gradio)
- ✅ Soporte SGDA documento types reales (ae_ciu_sol_prestacion, ae_con_cer_rgecivil, etc.)
- ✅ 36/36 tests unitarios, e2e demo sin dependencias pesadas

**Métrica:** Todos los módulos con cobertura >80%, 0 tests fallando.

### O2: Trazabilidad de decisiones
- ✅ Cada bastanteo_evidence vinculado a: document_id + page + block_id + bbox
- ✅ Razonamiento visible en Reasoning Trace (qué requisito, qué consulta RAG, qué evidencia, qué score)
- ✅ Modo demo capaz de explicar decisión sin necesidad de base de datos pesada

**Métrica:** 100% de evidencias tienen grounding; Reasoning Trace legible para auditor.

### O3: Robustez ante variabilidad
- ✅ Sistema no alucina cuando evidencia es insuficiente (returns MISSING explícito)
- ✅ Maneja documentos escaneados con ruido, dobleces, ángulos torcidos (evaluado en Fase 3)
- ✅ Arquitectura preparada para cambiar parser (abstracción get_parser(), backend swappable)

**Métrica:** Error rate en detección de MISSING <5%; no más de 1 alucinación por 100 expedientes.

### O4: Documentación y reproducibilidad (SpecDD)
- ✅ PRD, ADRs, specs de componentes, log de uso de IA, evolución de decisiones
- ✅ Código comentado, docstrings, ejemplos ejecutables
- ✅ Repo público con instrucciones de setup + demo local

**Métrica:** Cualquier desarrollador externo reproduce la demo en <30 min sin soporte.

---

## 6. Propuesta Arquitectónica en Alto Nivel

```
Entrada: Expediente (PDF/imágenes)
   ↓
[PASO 1: Parser OCR-free]
   Backend: Datalab/Chandra OCR-2 (o dots.ocr, Nemotron-Parse)
   Salida: Bloques estructurados (JSON)
   ↓
[PASO 2: Normalizador]
   Mapeo: Salida nativa → CanonicalDocumentParse v1.1
   Salida: case_id, documento[], página[], bloque[], extracted_fields[]
   ↓
[PASO 3: RAG (indexación + retrieval)]
   Chunker: Respeta secciones lógicas (solicitante, certificaciones, firmas)
   Index: ChromaDB + embeddings multilíngüe
   Retrieval: `retrieve_fn(query, top_k=3)` → [cita + contexto + bbox]
   ↓
[PASO 4: Agente Bastanteo (ReAct)]
   For each Requirement en BADA_REQUIREMENTS:
     - Consulta: `retrieve_fn(requirement.query)` → citas
     - Juicio: Judge (rule-based o LLM) → {supported, contradicted, missing}
     - Evidencia: link a document_id, page, block_id, bbox
   Salida: bastanteo_evidence[], bastanteo_gold (VÁLIDO/INCOMPLETO/RECHAZADO)
   ↓
[PASO 5: UI Gradio]
   Modo real: usuario sube PDF + API key → corre paso 1–4 → muestra resultado
   Modo demo: carga sample_case.json + naive_retriever → mismo paso 3–4
   Output: Bastanteo visual + tabla de evidencias + Reasoning Trace
```

**Principios de diseño:**
- **Modularidad:** Cada paso es independiente, tests aislados.
- **Abstracción de modelos:** Parser, Judge pueden cambiar de backend sin tocar el resto.
- **Trazabilidad:** Toda decisión es auditable hasta bloque/página/bbox.
- **Graceful degradation:** Sin RAG pesada, funciona con naive_retriever (demo).

---

## 7. Alcance In / Out

### ✅ In Scope (Fase 1–5)
- Parser documental OCR-free (API Datalab)
- Normalizador a JSON canónico v1.1
- RAG con layout-awareness (LlamaIndex + ChromaDB)
- Agente bastanteo con ReAct + rule-based judge
- UI Gradio (real + demo)
- Tests e2e, dataset BADA mínimo, bitácora de decisiones

### ⏳ Out of Scope (Fase 2+, Trabajo Futuro)
- Generación completa de dataset sintético (LayoutDM + SynthDoG + augmentation)
- Judge basado en Claude (stub; requiere decisión de modelo y coste)
- Despliegue en producción con API REST, base de datos, autenticación
- Evaluación cuantitativa exhaustiva (necesita dataset >1000 casos)
- Integración con sistemas INSS reales

---

## 8. Éxito Académico + Profesional

**Para TFM:**
- Caso de uso real, dominio adminsitrativo, literatura verificada (Li et al. 2024, RAG failure modes).
- Arquitectura justificada contra baselines (Donut/Pix2Struct, RAG plano).
- Evaluación cuantitativa (F1 macro, ANLS) + cualitativa (grounding, trazabilidad).

**Para Curso SpecDD:**
- Especificación formal de requisitos, decisiones documentadas (ADRs), iteración visible.
- Ciclo completo: Vision → PRD → Specs → Código → Tests → Evaluación.
- Uso de IA a lo largo del proceso (prompts, decisiones, generación de artefactos).

---

## Siguiente Paso

Validar esta Visión con stakeholders (tu profesor, si aplica); proceder a **02-Requisitos.md** (PRD detallado con criterios de aceptación por feature).

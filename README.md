# TFM-Code — Pipeline Agentic E2E de Bastanteo Administrativo

**Proyecto:** Arquitecturas agénticas end-to-end para bastanteo administrativo documental en AA.PP. (INSS/GISS)  
**Versión:** 0.1.0 | **Python:** ≥3.10 | **Metodología:** CRISP-DM + SpecDD

## 🎯 Objetivo

Automatizar **bastanteo documental administrativo** mediante un pipeline integrado sin OCR local:
```
Documento (PDF/imagen)  
  ↓ Parser (Datalab API)  
  → JSON bloques + bbox  
  ↓ Normalizer (v1.1)  
  → Esquema canónico  
  ↓ RAG (ChromaDB)  
  → Retrieval layout-aware  
  ↓ Agent (ReAct)  
  → Evidencia trazable  
  ↓ UI (Gradio)  
  → Demo interactiva  
```

## 📦 Módulos Core

### **Parser** (`04_src/parser/`)
Convierte documentos (PDF/imagen) → JSON estructurado con bloques y bounding boxes.
- **Backend:** API Datalab (propietario, 86.7% acc)
- **Justificación:** sin GPU local; Chandra OCR-2 prohibitivo; migración a OCR abierto = trabajo futuro
- **Salida:** `ParserResult` (bloques + calidad 0-5)
- **CLI:** `python 04_src/parser/run_parser.py ruta/doc.pdf --mode accurate --format json`
- **Arquitectura extensible:** factory pattern para soportar backends (`chandra-hf`, `dots.ocr`, etc.)

### **Normalizer** (`04_src/normalizer/`)
Mapea JSON parser → esquema canónico v1.1 (`CanonicalDocumentParse`).
- **Responsabilidades:** validación JSON Schema + tipado Pydantic + metadatos obligatorios
- **NO incluye:** llamadas a LLM ni acoplamiento a UI
- **Pipeline:** `build_document_entry()` → `build_case_envelope()` → `validate(part="case")`
- **⚠️ Crítico:** mapeo Datalab → v1.1 requiere **validación con datos reales** antes de producción

### **RAG** (`04_src/rag/`)
Chunking layout-aware + embeddings + vector store + retrieval con scoring.
- **Componentes:**
  - `chunking.py`: agrupa bloques respetando secciones (max 1000 chars), preserva metadatos
  - `index_store.py`: LlamaIndex + ChromaDB, embedding `intfloat/multilingual-e5-small` (CPU)
- **Outputs:** chunks trazables (document_id, página, sección, bbox, block_ids)
- **Interfaz:** `build_chunks()` → `build_nodes()` → `build_index()` + `query(top_k=3)`

### **Agent** (`04_src/agent/`)
Orquesta ciclo **ReAct de bastanteo** con evidencia trazable.
- **Pipeline:** retrieve RAG → comparar campos contra requerimientos → construir bastanteo_evidence + bastanteo_gold
- **Interfaz:** `RuleBasedJudge` (determinista, funcional) + `LLMJudge` (interface, TBD)
- **Catálogo:** requerimientos (placeholder; mapa real pendiente)
- **Abierta:** VLM vs LLM para juez (operable sobre JSON, no imagen cruda)

### **UI** (`04_src/ui/`)
Demo mínima en Gradio — orquesta todo el pipeline visualmente.
- **Arquitectura limpia:** `pipeline.py` (sin Gradio) + `app.py` (Gradio)
- **Modos:**
  - **Real:** PDF → Datalab + ChromaDB (requiere `DATALAB_API_KEY`)
  - **Demo:** `sample_case.json` + `naive_retriever` (sin API, sin deps pesadas)
- **Ejecución:** `python 04_src/ui/app.py`

## ⚡ Inicio Rápido

```bash
# Instalar dependencias
pip install -e .

# (Opcional) Configurar credenciales
cp .env.example .env  # añade DATALAB_API_KEY

# Demo sin API
python 04_src/ui/app.py  # Abre Gradio en browser

# Tests
pytest -v
```

## 🏗️ Estructura del Proyecto

```
TFM-Code/
├── 01_admin/          → Documentación administrativa (notas de proyecto)
├── 03_data/           → Datasets y muestras (sample_case.json compartido con UI)
├── 04_src/            → Código fuente (5 paquetes Python importables)
│   ├── parser/        → Parsing (Datalab API)
│   ├── normalizer/    → Normalización (esquema v1.1)
│   ├── rag/           → Retrieval agentic (ChromaDB + LlamaIndex)
│   ├── agent/         → Orquestación ReAct (juez + bastanteo)
│   └── ui/            → Demo Gradio
├── 05_eval/           → Evaluación (métricas, benchmarks)
├── 06_docs/           → Documentación técnica (arquitectura, decisiones)
├── specs/             → Especificaciones
│   ├── canonical-document-parse-v1.1.md     → Esquema unificado con mapeos
│   └── canonical_document_parse.schema.json  → Validación JSON Schema
├── tests/             → Suite de tests (39 casos cubiertos)
├── claude-framework/  → Marcos persistentes (PERSONA, RULES, COMMANDS)
├── CLAUDE.md          → Contexto IA automático
├── conftest.py        → Configuración pytest (sys.path para 04_src/)
└── pyproject.toml     → Metadata + deps (setuptools mapea 04_src/ → importables)
```

**Nota:** Carpetas `01_admin`, `03_data`, etc. siguen numeración CRISP-DM. `04_src/` NO es paquete Python (identificador no puede empezar por dígito), pero sus subcarpetas SÍ son paquetes importables tras `pip install -e .`.

## 🧪 Tests (39 casos cubiertos)

| Módulo | Archivo | Casos | Cobertura |
|--------|---------|-------|-----------|
| **Parser** | `test_datalab_client.py` | 4 | Success, file missing, API key missing, unknown backend |
| **Normalizer** | `test_normalizer.py` | 5 | Tipos/bbox, fallback, agrupación, schema validation, document_type_pred |
| **RAG** | `test_chunking.py` | 6 | Secciones, cambio sección, presupuesto char, header, bbox, chunk_id |
| | `test_index_store.py` | 3 | Metadatos, build+query, persistencia ChromaDB |
| **Agent** | `test_judge.py` | 6 | Missing sin citas, supported score, threshold, factory, unknown, LLM pending |
| | `test_bastanteo.py` | 4 | All required, missing required, optional OK, traceability |
| | `test_integration.py` | 2 | Schema post-bastanteo, missing requirement |
| **UI** | `test_pipeline.py` | 5 | Demo case, agent e2e, citations, missing API key, missing deps |
| | `test_naive_retriever.py` | 4 | DNI lookup, no overlap, top_k, shape match |

**Estrategia:** mocks (pytest-mock) para evitar APIs reales, fixtures sintéticas para RAG, validación JSON Schema en integración.

## ⚙️ Configuración

### Dependencias Core
- **Parsing:** `datalab-python-sdk`, `python-dotenv`
- **Normalización:** `jsonschema`, `pydantic>=2`
- **RAG:** `llama-index-core`, `chromadb`, `llama-index-embeddings-huggingface`
- **UI:** `gradio`
- **Dev:** `pytest`, `pytest-mock`

### Variables de Entorno
```bash
DATALAB_API_KEY=<tu_clave>  # Para modo real
```

## 📖 Marcos Persistentes (Claude Context)

- **CLAUDE.md** — Carga automática en cada sesión
- **claude-framework/**
  - `PERSONA.md` — Rol: asistente técnico académico
  - `RULES.md` — Estilo conciso (≤400 palabras salvo detalle explícito)
  - `COMMANDS.md` — 6 comandos: `/tfm-section`, `/tfm-review`, `/spec`, `/lti-tests`, `/refactor-code`, `/resume`

## ⚠️ Notas Críticas & Pendiente

### Completado ✅
- Interfaz unificada `CanonicalDocumentParse v1.1` (consolidación de esquemas)
- Parser con API Datalab (funcional, tests cubiertos)
- Normalizer con validación v1.1 (funcional)
- RAG chunking layout-aware + ChromaDB (funcional, embeddings CPU)
- Agent ReAct con juez rule-based (funcional)
- UI Gradio modos demo/real (funcional)
- Suite de 39 tests con mocks e integración

### Pendiente ⚠️
- **Mapeo Datalab → v1.1:** validar con documentos REALES antes de producción
- **Mapa documental:** `catalog.py` es placeholder; requirements finales TBD
- **VLM vs LLM:** confirmar si agente necesita capacidad multimodal
- **LLMJudge:** interface definida pero no implementada
- **OCR abierto:** migración futura (actualmente Datalab propietaria, 86.7% acc)
- **Base de datos real:** tests con sintético; producción requiere casos INSS/GISS

## 📚 Referencias

- Esquema canónico: [specs/canonical-document-parse-v1.1.md](specs/canonical-document-parse-v1.1.md)
- JSON Schema: [specs/canonical_document_parse.schema.json](specs/canonical_document_parse.schema.json)

---

**Contacto:** Proyecto TFM 2024-2025 | Código limpio para producción

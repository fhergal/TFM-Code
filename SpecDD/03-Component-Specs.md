# Especificaciones de Componentes — Contratos de Entrada/Salida

**Versión:** 1.0 · **Fecha:** Julio 2026
**Propósito:** Definir el contrato formal (entrada, salida, invariantes, errores) de cada módulo del pipeline, de modo que cualquier componente pueda sustituirse sin romper los demás.

---

## Principio rector

> Todo módulo se comunica con el resto **exclusivamente** a través del contrato `CanonicalDocumentParse v1.1`
> (`specs/canonical_document_parse.schema.json`) o de tipos derivados de él.
> Ningún módulo consume la salida nativa de otro (formato propietario de parser, objetos de LlamaIndex, etc.).

Consecuencia práctica: cambiar Datalab por dots.ocr, o ChromaDB por Qdrant, no altera la firma de ninguna función aguas abajo.

---

## C1 · Parser documental

**Módulo:** `04_src/parser/` (`base.py`, `datalab_client.py`, `chandra_hf_client.py`, `run_parser.py`)
**Requisitos cubiertos:** REQ-1.1 … REQ-1.5

### Interfaz

```python
class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str | Path, output_format: str = "json") -> ParserResult: ...

def get_parser(backend: str = "datalab", **kwargs) -> DocumentParser: ...
```

### Contrato

| | Descripción |
|---|---|
| **Entrada** | `file_path`: ruta a PDF/imagen existente · `output_format`: `"json"` \| `"markdown"` · (config) `backend`, `mode`, `api_key` |
| **Salida** | `ParserResult` (dataclass) |
| **Efectos** | Llamada de red a la API de Datalab (backend `datalab`); ninguno en `chandra-hf` (stub) |

### Estructura de `ParserResult`

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `source_path` | `Path` | sí | Trazabilidad del origen |
| `backend` | `str` | sí | `"datalab"` \| `"chandra-hf"` |
| `model_name` | `str` | sí | Incluye el `mode` usado (auditoría de coste/calidad) |
| `output_format` | `str` | sí | Formato realmente devuelto |
| `raw` | `dict \| str` | sí | Salida nativa **sin normalizar** — solo la consume C2 |
| `page_count` | `int \| None` | no | `None` si el backend no lo expone |
| `quality_score` | `float \| None` | no | Rango [0, 1]; alimenta `parser.confidence_global` |
| `elapsed_seconds` | `float` | sí | Métrica de eficiencia (REQ de evaluación) |
| `extra_metadata` | `dict` | sí | `cost_breakdown`, `checkpoint_id`, … |

### Errores

| Excepción | Causa | Contrato |
|---|---|---|
| `ImportError` | Falta `datalab-python-sdk` | Mensaje con el `pip install` exacto |
| `RuntimeError` | Falta `DATALAB_API_KEY` | Mensaje con la URL para obtener la clave |
| `FileNotFoundError` | Ruta inexistente | Incluye la ruta ofensiva |
| `ValueError` | `backend` desconocido en `get_parser()` | Lista los backends válidos |

### Invariantes

- `parse()` es **idempotente respecto al fichero**: no modifica el original.
- `raw` nunca es `None` (fallback defensivo si el SDK renombra atributos).
- El parser **no conoce** el esquema canónico: esa responsabilidad es exclusiva de C2.

---

## C2 · Normalizador

**Módulo:** `04_src/normalizer/` (`marker_blocks.py`)
**Requisitos cubiertos:** REQ-2.1 … REQ-2.5

### Interfaz

```python
def flatten_marker_tree(node: dict, page_number: int) -> list[dict]: ...
def normalize(result: ParserResult, case_id: str, procedure_type: str) -> dict: ...
```

### Contrato

| | Descripción |
|---|---|
| **Entrada** | `ParserResult` (salida de C1) + identificadores del expediente |
| **Salida** | `dict` que **valida contra** `specs/canonical_document_parse.schema.json` (v1.1) |
| **Efectos** | Ninguno (función pura, sin red ni disco) |

### Jerarquía garantizada en la salida

```
case (schema_version, case_id, procedure_type, case_context, expected_document_map)
 └── document_inventory[]  (document_id, document_type_pred, origin, document_metadata)
      └── pages[]          (page_number)
           └── blocks[]    (block_id, block_type, text, bbox, reading_order, semantics)
      └── extracted_fields[]      (opcional en v1.1)
      └── bastanteo_evidence[]    (lo rellena C4, no C2)
```

### Invariantes

- `block_id` es único en todo el expediente y sigue el patrón `DOC-####-P##-B###`.
- `bbox` siempre tiene las 4 coordenadas + `unit`; nunca parcial.
- `reading_order` es un entero ≥ 1, consecutivo dentro de cada página.
- `confidence_global` ∈ [0, 1] — **restricción del schema**; violarla hace fallar la validación
  (este fue un bug real detectado en tests: `quality_score=4.1` → corregido a `0.91`).
- Vocabulario cerrado de `block_type`: `title`, `section_header`, `paragraph`, `form_field`,
  `key_value`, `table`, `table_row`, `table_cell`, `checkbox`, `signature`, `stamp`,
  `image_region`, `header`, `footer`, `free_note`.

### Errores

| Excepción | Causa |
|---|---|
| `jsonschema.ValidationError` | Salida no conforme al schema; el mensaje indica la ruta JSON del campo infractor |
| `KeyError` | La salida nativa del parser cambió de forma (contrato roto aguas arriba) |

---

## C3 · RAG — Chunking, indexación y retrieval

**Módulo:** `04_src/rag/` (`chunking.py`, `index_store.py`) + fallback `04_src/ui/naive_retriever.py`
**Requisitos cubiertos:** REQ-3.1 … REQ-3.5

### Interfaz

```python
def build_chunks(case: dict) -> list[Chunk]: ...
def build_index(chunks: list[Chunk], persist_dir: str, embed_model=None) -> Index: ...
def make_retrieve_fn_from_index(index) -> Callable[[str, int], list[Citation]]: ...
def demo_retrieve_fn(case: dict) -> Callable[[str, int], list[Citation]]: ...   # fallback sin deps
```

### Contrato del chunker

| | Descripción |
|---|---|
| **Entrada** | `case`: `CanonicalDocumentParse` v1.1 validado (salida de C2) |
| **Salida** | `list[Chunk]`, cada uno con `text` + metadata completa de trazabilidad |
| **Regla de agrupación** | Por **sección lógica** (`semantics.section`), no por longitud fija de caracteres |

Metadata obligatoria arrastrada por cada chunk (esto es lo que hace posible el grounding en C4):

`document_id` · `page_number` · `block_id` · `block_type` · `bbox` · `section` · `entity_type?`

### Contrato del retriever

```python
retrieve_fn(query: str, top_k: int = 3) -> list[Citation]
```

`Citation` expone como mínimo: `text`, `score`, `document_id`, `page_number`, `block_id`, `bbox`.

**Punto clave de diseño:** `retrieve_fn` es una **closure**, no un método de clase. El agente (C4)
recibe una función, no un vector store. Por eso el mismo agente funciona sin cambios con
ChromaDB (modo real) o con el retriever naive por solapamiento léxico (modo demo).

### Invariantes

- Un chunk nunca parte un bloque de tipo `table`, `signature` o `stamp` por la mitad.
- `top_k` resultados como máximo; puede devolver menos (o cero) si no hay coincidencias.
- Devolver lista vacía es una **respuesta válida**, no un error — C4 la traduce a `missing`.

### Errores

| Excepción | Causa |
|---|---|
| `ImportError` | Faltan `llama-index` / `chromadb` en modo real → la UI debe degradar a modo demo |
| `ValueError` | `case` sin bloques indexables |

---

## C4 · Agente de bastanteo

**Módulo:** `04_src/agent/` (`base.py`, `judge.py`, `bastanteo.py`, `catalog.py`)
**Requisitos cubiertos:** REQ-4.1 … REQ-4.7

### Interfaz

```python
@dataclass
class Requirement:
    requirement_id: str      # código SGDA real, p. ej. "ae_ciu_sol_prestacion"
    claim: str               # afirmación a verificar, en lenguaje natural
    query: str               # consulta de recuperación asociada
    requirement_type: str    # "obligatorio" | "condicional"
    evidence_type: str       # "documento" | "campo" | "firma" | "sello"

class Judge(ABC):
    @abstractmethod
    def judge(self, claim: str, citations: list[Citation]) -> Verdict: ...

def get_judge(backend: str = "rule-based", **kwargs) -> Judge: ...
def run_bastanteo(case, retrieve_fn, requirements=BADA_REQUIREMENTS, judge=None) -> dict: ...
```

### Contrato

| | Descripción |
|---|---|
| **Entrada** | `case` (v1.1) · `retrieve_fn` (closure de C3) · catálogo de `Requirement` · `Judge` |
| **Salida** | `case` enriquecido con `bastanteo_evidence[]` y `bastanteo_gold` |
| **Efectos** | Red **solo** si el judge es `anthropic`; con `rule-based` es totalmente local |

### Ciclo ReAct (una iteración por requisito)

```
para cada Requirement r en el catálogo:
    citations = retrieve_fn(r.query, top_k=3)      # Act:    recuperar
    verdict   = judge.judge(r.claim, citations)     # Reason: juzgar evidencia
    evidence  = Evidence(r, verdict, citations)     # Observe: anclar y registrar
    bastanteo_evidence.append(evidence)
dictamen = agregar(bastanteo_evidence)              # VÁLIDO | INCOMPLETO | RECHAZADO
```

Cada requisito genera **una consulta de recuperación independiente y un juicio independiente**.
Esta descomposición (en espíritu análoga a Self-Route, Li et al., EMNLP 2024) es lo que produce
la traza auditable: cada afirmación del dictamen final tiene su propia cadena evidencia→decisión.

### Estructura de `bastanteo_evidence[]`

| Campo | Tipo | Notas |
|---|---|---|
| `evidence_id` | `str` | Único dentro del expediente |
| `requirement_id` | `str` | Código SGDA (enlaza con `expected_document_map`) |
| `claim` | `str` | Afirmación verificada |
| `status` | `str` | `supported` \| `contradicted` \| `missing` |
| `score` | `float` | Confianza del judge, [0, 1] |
| `source_document_id` | `str \| None` | `None` si `status == "missing"` |
| `source_page` | `int \| None` | ídem |
| `source_block_ids` | `list[str]` | Vacía si `missing` |
| `span_text` | `str \| None` | Fragmento literal que fundamenta la decisión |

### Reglas de decisión (`bastanteo_gold`)

| Situación | Dictamen |
|---|---|
| Todos los `obligatorio` en `supported` | `VÁLIDO` |
| Algún `obligatorio` en `missing` | `INCOMPLETO` |
| Algún requisito en `contradicted` (p. ej. DNI discordante entre documentos) | `RECHAZADO` |

### Invariantes — el más importante del sistema

> **No-alucinación:** si `citations == []` o `score < threshold`, el estado es `missing`
> y `source_*` queda a `None`. El agente **nunca** infiere, completa ni parafrasea evidencia
> que no haya recuperado literalmente del expediente.

Otros:
- El agente es **agnóstico al vector store**: solo ve `retrieve_fn`.
- El agente es **agnóstico al judge**: `rule-based` y `anthropic` son intercambiables por factory.
- La longitud de `bastanteo_evidence` es siempre igual al número de requisitos evaluados
  (8 para BADA) — verificado en test e2e.

### Errores

| Excepción | Causa |
|---|---|
| `TypeError` | Instanciar un `Judge` abstracto sin implementar `judge()` (bug real detectado en `AnthropicJudge`) |
| `NotImplementedError` | `AnthropicJudge.judge()` — stub declarado, aún no implementado |

---

## C5 · Interfaz de usuario (orquestación + Gradio)

**Módulo:** `04_src/ui/` (`pipeline.py`, `app.py`, `naive_retriever.py`, `sample_case.json`)
**Requisitos cubiertos:** REQ-5.1 … REQ-5.6

### Interfaz de orquestación (`pipeline.py`)

```python
def load_demo_case() -> dict: ...
def process_document(file_path, api_key) -> dict: ...          # C1 → C2
def build_index_for_case(case) -> Index: ...                    # C3
def make_retrieve_fn_from_index(index) -> RetrieveFn: ...       # C3
def ask_question(retrieve_fn, question) -> list[Citation]: ...  # consulta libre
def run_bastanteo_over_case(case, retrieve_fn) -> dict: ...     # C4
def demo_retrieve_fn(case) -> RetrieveFn: ...                   # C3 fallback
```

### Los dos modos

| | Modo **real** | Modo **demo** |
|---|---|---|
| Entrada | PDF/imagen del usuario + `DATALAB_API_KEY` | `sample_case.json` (expediente BADA de 6 documentos) |
| Parser | C1 con backend `datalab` | — (el caso ya está normalizado) |
| Retrieval | C3 con LlamaIndex + ChromaDB + embeddings | `naive_retriever` (solapamiento léxico tipo Jaccard) |
| Agente | **el mismo código de C4** | **el mismo código de C4** |
| Dependencias | Pesadas (red, GPU-free pero API) | Ninguna más allá de la stdlib + Gradio |

**Decisión de diseño deliberada:** ambos modos atraviesan el **mismo** agente real. El modo demo
degrada únicamente la calidad del *retrieval*, nunca sustituye ni simula la lógica de bastanteo.
Lo que se ve en la demo es el sistema de verdad, con un recuperador peor.

### Salida al usuario

1. **Tabla de bastanteo:** una fila por requisito → `claim`, `status`, `span_text`, `source_page`.
2. **Reasoning Trace:** para cada requisito, la consulta lanzada, las citas recuperadas con su score,
   y el veredicto — con `document_id` + `page` + `block_id` explícitos.
3. **Consulta libre:** campo de texto → `ask_question()` → tabla de citas con su localización.

### Errores

`process_document()` captura `(RuntimeError, ValueError, ImportError)` de `get_parser()` y las
traduce a `PipelineError` con mensaje legible para el usuario final (bug real corregido:
originalmente no capturaba `ImportError`, por lo que la falta del SDK rompía la UI con un traceback).

---

## Matriz de acoplamiento

| Componente | Conoce a… | **No** conoce a… |
|---|---|---|
| C1 Parser | La API del backend | El esquema canónico, el RAG, el agente |
| C2 Normalizador | `ParserResult` + el schema v1.1 | El backend concreto, el RAG, el agente |
| C3 RAG | El schema v1.1 | El parser, los requisitos de bastanteo |
| C4 Agente | El schema v1.1 + `retrieve_fn` + `Judge` | El parser, el vector store, el LLM concreto |
| C5 UI | Todos (es el orquestador) | — |

El acoplamiento es estrictamente **descendente y por contrato**: ningún componente aguas abajo
importa nada del backend concreto de un componente aguas arriba.

---

## Cobertura de tests por componente

| Componente | Fichero de test | Estado |
|---|---|---|
| C1 Parser | `tests/parser/` | ✅ Con mocks del SDK de Datalab |
| C2 Normalizador | `tests/normalizer/test_normalizer.py` | ✅ Validación real contra el JSON Schema |
| C3 Chunking | `tests/rag/test_chunking.py` | ✅ 6/6 |
| C3 Index store | `tests/rag/test_index_store.py` | ⚠️ Escrito, con `pytest.skip()`: requiere `chromadb`/`llama-index` |
| C4 Agente | `tests/agent/` | ✅ Salida validada contra el schema |
| C5 UI | `tests/ui/test_pipeline.py` | ✅ e2e: carga caso → recupera → agente → 8 evidencias |

**Total: 36/36 tests en verde** (excluyendo `test_index_store.py`, pendiente de ejecutar en entorno
con las dependencias pesadas instaladas).

---

## Siguiente paso

Ver `ADRs/` para el razonamiento y las alternativas descartadas detrás de cada uno de estos contratos.

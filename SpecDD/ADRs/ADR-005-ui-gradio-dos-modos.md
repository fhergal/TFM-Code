# ADR-005 · UI Gradio con modo real y modo demo sobre el mismo agente

**Estado:** Aceptada
**Fecha:** Julio 2026 (Fase 5)
**Decisores:** Fer (autor), asistido por Claude
**Requisitos afectados:** REQ-5.1 … REQ-5.6

---

## Contexto

El sistema tiene que demostrarse en dos escenarios muy distintos:

1. **Uso real:** documento propio del usuario + `DATALAB_API_KEY` + pila RAG completa
   (LlamaIndex, ChromaDB, modelo de embeddings).
2. **Defensa y demostración:** presentación en directo, posiblemente sin red fiable, sin clave de
   API a mano y sin garantía de que las dependencias pesadas estén instaladas en la máquina.

Restricción adicional constatada durante el desarrollo: en el entorno de trabajo no fue posible
instalar `chromadb` ni `llama-index` (red demasiado lenta), lo que confirmó que **depender de la
pila pesada para poder enseñar el sistema es un riesgo real**, no hipotético.

Riesgo académico asociado: una "demo" que sustituya la lógica por respuestas preparadas no
demuestra nada. Sería una maqueta, no el sistema.

## Decisión

Una única UI en Gradio con **dos modos que comparten el agente real**:

| | Modo **real** | Modo **demo** |
|---|---|---|
| Entrada | PDF/imagen + `DATALAB_API_KEY` | `sample_case.json` (expediente BADA, 6 documentos) |
| Parser (C1) | Datalab / Chandra | — (el caso ya viene normalizado) |
| Normalizador (C2) | Sí | — (ya aplicado al fixture) |
| Chunking (C3) | Layout-aware | **Layout-aware, el mismo** |
| Retrieval (C3) | ChromaDB + embeddings multilingües | `naive_retriever` (solapamiento léxico) |
| Agente (C4) | **El mismo código** | **El mismo código** |
| Dependencias | Pesadas | stdlib + Gradio |

Regla que hace válida la demo:

> El modo demo degrada **únicamente la función de puntuación del recuperador**.
> No simula, no sustituye ni cortocircuita la lógica de bastanteo.
> Lo que se ve en la demo es el sistema real, con un recuperador peor.

El fixture `sample_case.json` usa además **datos de dominio reales**: procedimiento
`aex_gestprestaciones_bada`, tipologías SGDA auténticas (`ae_ciu_sol_prestacion`,
`ae_con_cer_rgecivil`, …) y textos en castellano administrativo verosímil.

## Consecuencias

**Positivas**
- La demo funciona sin red, sin clave y sin GPU: riesgo de presentación en directo prácticamente
  eliminado.
- El test e2e (`test_demo_retrieve_fn_runs_full_agent_end_to_end`) recorre el agente **real** y
  verifica las 8 evidencias → el modo demo es a la vez vitrina y arnés de pruebas.
- Un evaluador externo reproduce el sistema en minutos, sin darse de alta en ningún servicio.
- El contraste entre ambos modos ilustra de forma didáctica el efecto de la calidad del retrieval
  manteniendo todo lo demás constante.

**Negativas / coste asumido**
- Dos rutas de código que mantener en `pipeline.py`, con su detección de modo.
- El modo demo da resultados **peores** por diseño; hay que explicarlo al presentar para que no se
  interprete como límite de la arquitectura.
- El fixture puede quedar desactualizado respecto al catálogo de requisitos: mitigado con
  aserciones explícitas en los tests (`len(document_inventory) == 6`, `len(bastanteo_evidence) == 8`).

**Bug real encontrado gracias a esta separación**
`process_document()` solo capturaba `(RuntimeError, ValueError)` de `get_parser()`, pero la ausencia
del SDK de Datalab lanza `ImportError` — la UI se rompía con un traceback en lugar de degradar
limpiamente. Corregido añadiendo `ImportError` al bloque de captura y traduciéndolo a `PipelineError`.

## Alternativas consideradas y descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Solo modo real | Depende de red, clave y dependencias pesadas: riesgo inasumible en una defensa en directo |
| Demo con respuestas pregrabadas | No demuestra el sistema; académicamente indefendible |
| Notebook Jupyter en lugar de UI | Menos accesible para perfiles no técnicos (funcionario, auditor), que son dos de los tres usuarios objetivo |
| Streamlit | Equivalente en prestaciones; se elige Gradio por menor fricción para exponer una demo compartible. Decisión reversible y de bajo impacto |
| API REST + frontend propio | Fuera del alcance del TFM; queda como trabajo futuro para despliegue en producción |

## Referencias

- `04_src/ui/app.py`, `pipeline.py`, `naive_retriever.py`, `sample_case.json`
- `tests/ui/test_pipeline.py`
- Guía de preparación de la demostración (carpeta `TFM-Burocracy`)

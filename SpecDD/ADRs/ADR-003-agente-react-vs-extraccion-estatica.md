# ADR-003 · Agente ReAct por requisito frente a extracción estática o LLM generativo directo

**Estado:** Aceptada
**Fecha:** Julio 2026 (Fase 4)
**Decisores:** Fer (autor), asistido por Claude
**Requisitos afectados:** REQ-4.1 … REQ-4.7 · Valida la hipótesis **H3** de la memoria

---

## Contexto

El bastanteo consiste en verificar un conjunto de comprobaciones normativas sobre un expediente
(¿está la solicitud firmada?, ¿hay documento identificativo?, ¿el certificado de matrimonio es
exigible en este caso?). En el procedimiento BADA son **8 requisitos**, unos obligatorios y otros
condicionales, cada uno con su código SGDA real.

En el dominio administrativo, una decisión sin justificación trazable **no es utilizable**: el
funcionario responde legalmente de ella y el auditor debe poder reconstruirla. Esto descarta de
entrada cualquier arquitectura cuya salida sea un veredicto sin anclaje documental.

Tres arquitecturas candidatas:

1. **Extracción estática campo a campo:** reglas fijas que buscan cada campo en una posición esperada.
2. **LLM generativo directo:** meter el expediente entero en el contexto y pedir el dictamen.
3. **Agente ReAct descompuesto por requisito:** una consulta de recuperación y un juicio por comprobación.

## Decisión

Se adopta la opción 3: un **ciclo ReAct con un `Requirement` como unidad atómica**.

```python
para cada Requirement r:
    citations = retrieve_fn(r.query, top_k=3)   # Act
    verdict   = judge.judge(r.claim, citations) # Reason
    evidence  = Evidence(r, verdict, citations) # Observe → registrar
```

Decisiones de diseño asociadas:

- El catálogo `BADA_REQUIREMENTS` usa **códigos SGDA reales**, no etiquetas inventadas.
- El `Judge` es intercambiable por factory: `RuleBasedJudge` (heurístico, local, sin red) por
  defecto; `AnthropicJudge` declarado como stub para sustituirlo por un LLM más adelante.
- El agente recibe `retrieve_fn` como **función**, no un vector store → es agnóstico al RAG.
- **Invariante de no-alucinación:** si no hay citas o el score está por debajo del umbral, el estado
  es `missing` con `source_*` a `None`. El agente nunca completa evidencia que no haya recuperado.

Esta descomposición es **análoga en espíritu** a Self-Route (Li et al., EMNLP 2024 Industry Track),
que enruta cada consulta al mecanismo adecuado en lugar de procesar todo el contexto de una vez.
Se declara explícitamente como analogía conceptual, **no** como implementación de ese paper.

## Consecuencias

**Positivas**
- Cada afirmación del dictamen tiene su propia cadena consulta → citas → veredicto: la Reasoning
  Trace es auditable requisito a requisito, que es exactamente lo que exige H3.
- Los requisitos condicionales se modelan de forma natural (`requirement_type`), sin ramificaciones
  ad hoc en el código.
- Añadir un procedimiento nuevo (otra prestación del INSS) es **escribir un catálogo**, no tocar el agente.
- Sin LLM en el camino crítico por defecto: la demo corre offline, sin coste y sin latencia de red.
- `len(bastanteo_evidence) == len(requirements)` siempre → invariante verificable en test e2e.

**Negativas / coste asumido**
- N consultas de recuperación en lugar de una: mayor latencia total (aceptable con N=8; habría que
  revisarlo con N≫50).
- El `RuleBasedJudge` por similitud léxica es frágil ante paráfrasis. Es una decisión consciente:
  se prefiere un juez **predecible y explicable** para el prototipo, dejando el juez LLM como
  siguiente iteración ya prevista en la interfaz.

## Alternativas consideradas y descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Extracción estática campo a campo | No registra de forma nativa *por qué* se dio por cumplido un requisito; frágil ante variación de plantilla; no modela condicionalidad |
| LLM generativo sobre el expediente completo | Alto riesgo de alucinación sin grounding; coste y latencia elevados; la traza es una explicación *post hoc*, no el mecanismo real de decisión — inaceptable para auditoría administrativa |
| RAG plano de una sola consulta + resumen | Mezcla evidencias de requisitos distintos; imposible atribuir qué cita sustenta qué comprobación |
| Implementar literalmente Self-Route | Excede el alcance del TFM y exigiría el aparato experimental de contexto largo del paper; se cita como fundamentación, no como implementación |

## Referencias

- `04_src/agent/base.py`, `bastanteo.py`, `judge.py`, `catalog.py`
- `tests/ui/test_pipeline.py::test_demo_retrieve_fn_runs_full_agent_end_to_end` (8 evidencias)
- Li, Z., Li, C., Zhang, M., Mei, Q., & Bendersky, M. (2024). *Retrieval Augmented Generation or
  Long-Context LLMs? A Comprehensive Study and Hybrid Approach.* EMNLP 2024, Industry Track.
  — **Nota de verificación:** el paper sostiene reducción de coste de cómputo manteniendo rendimiento
  comparable al contexto largo. La cifra de "15–30% de mejora de precisión" que circula asociada a
  este trabajo procede en realidad de un blog comercial ajeno y **no es citable**; no se le atribuye.

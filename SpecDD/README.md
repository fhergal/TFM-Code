# SpecDD — Artefactos metodológicos

Carpeta de **artefactos de especificación** del proyecto, entregable del curso de Spec-Driven
Development. No contiene código: el código vive en `04_src/` y se comparte con el TFM.

> **Decisión de organización:** un único repositorio. El proyecto del curso y el TFM son el mismo
> sistema técnico documentado con dos énfasis distintos. Duplicar el código para "desacoplarlos"
> habría creado una divergencia inmediata sin ningún beneficio.

---

## Índice de artefactos

| # | Artefacto | Fichero | Qué responde |
|---|---|---|---|
| 1 | **Visión del producto** | [`01-Vision.md`](01-Vision.md) | Qué problema resolvemos, para quién, con qué restricciones y objetivos medibles |
| 2 | **Requisitos funcionales (PRD)** | [`02-Requisitos.md`](02-Requisitos.md) | Qué debe hacer el sistema: 36 requisitos priorizados con criterios de aceptación |
| 3 | **Especificaciones de componentes** | [`03-Component-Specs.md`](03-Component-Specs.md) | Contratos de entrada/salida, invariantes y errores de cada módulo |
| 4 | **Decisiones de arquitectura** | [`ADRs/`](ADRs/) | Por qué se decidió cada cosa y qué alternativas se descartaron |
| 5 | **Log de uso de IA** | [`04-Log-IA.md`](04-Log-IA.md) | Qué se delegó a IA, qué salió bien y qué hubo que corregir |
| 6 | **Evidencia de iteración** | [`05-Evolution-Specs.md`](05-Evolution-Specs.md) | Cómo evolucionaron las specs del Hilo 02 hasta el código final |

### Registro de decisiones (ADRs)

| ADR | Decisión | Hipótesis relacionada |
|---|---|---|
| [001](ADRs/ADR-001-abstraccion-parser.md) | Abstracción del parser con backends intercambiables | H1 |
| [002](ADRs/ADR-002-contrato-canonico.md) | `CanonicalDocumentParse v1.1` como contrato único | transversal |
| [003](ADRs/ADR-003-agente-react-vs-extraccion-estatica.md) | Agente ReAct por requisito vs. extracción estática | H3 |
| [004](ADRs/ADR-004-chunking-layout-aware.md) | Chunking sensible al layout vs. longitud fija | H2 |
| [005](ADRs/ADR-005-ui-gradio-dos-modos.md) | UI con modo real y modo demo sobre el mismo agente | — |

---

## Orden de lectura sugerido

Para un evaluador que llega por primera vez:

1. `01-Vision.md` — el problema y por qué merece la pena resolverlo.
2. `02-Requisitos.md` — qué se comprometió a construir.
3. `ADRs/` — las decisiones difíciles y su justificación (es donde está el pensamiento de diseño).
4. `03-Component-Specs.md` — cómo encajan las piezas.
5. `05-Evolution-Specs.md` — qué cambió respecto a lo planeado y por qué.
6. `04-Log-IA.md` — cómo se usó la IA y dónde hizo falta supervisión humana.

---

## Relación con el resto del repositorio

```
TFM-Code/
├── SpecDD/            ← artefactos metodológicos (esta carpeta)
├── specs/             ← contrato canónico: JSON Schema + documentación
├── 04_src/            ← código: parser, normalizer, rag, agent, ui
├── tests/             ← 36 tests (parser, normalizer, agent, rag, ui)
├── 03_data/           ← datos y fixtures
├── 05_eval/           ← evaluación (fase 3, pendiente)
└── 06_docs/           ← documentación general
```

La bitácora cronológica del proyecto está fuera del repositorio, junto a la memoria:
`TFM-Burocracy/Bitacora_Proyecto_TFM-SpecDD.md`.

---

## Estado

| Fase | Estado |
|---|---|
| 1 · Parser | ✅ Completo (tests con mocks) |
| 2 · Normalizador | ✅ Completo (validación contra JSON Schema) |
| 3 · RAG | ⚠️ Chunking verificado (6/6); indexación escrita, sin verificar por falta de dependencias pesadas en el entorno |
| 4 · Agente de bastanteo | ✅ Completo (8 requisitos SGDA reales) |
| 5 · UI Gradio | ✅ Completo (modo real + modo demo) |
| Artefactos SpecDD | ✅ Completos (6 documentos + 5 ADRs) |

**Tests:** 36/36 en verde (excluido `tests/rag/test_index_store.py`, marcado con `skip` a la espera
de un entorno con `chromadb` y `llama-index` instalados).

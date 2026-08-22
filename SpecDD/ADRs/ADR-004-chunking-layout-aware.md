# ADR-004 · Chunking sensible al layout frente a troceado por longitud fija

**Estado:** Aceptada
**Fecha:** Julio 2026 (Fase 3)
**Decisores:** Fer (autor), asistido por Claude
**Requisitos afectados:** REQ-3.1, REQ-3.5 · Valida la hipótesis **H2** de la memoria

---

## Contexto

El RAG clásico trocea el texto en fragmentos de longitud fija (por caracteres o tokens) con un
solapamiento configurable. Ese enfoque está diseñado para prosa continua y funciona mal en
documentos administrativos, que son mayoritariamente **formularios, tablas y certificados**.

Problema concreto observado en el dominio: un corte a mitad de un bloque `form_field` separa la
etiqueta de su valor ("DNI del solicitante:" en un chunk, "12345678Z" en el siguiente). El
recuperador puede entonces devolver el valor sin su etiqueta, o la etiqueta sin su valor — y el
juicio de evidencia se vuelve inútil.

Existe además una tensión estructural documentada en la literatura sobre modos de fallo del RAG:
los chunks pequeños (~100–256 tokens) favorecen la precisión de recuperación, mientras que los
grandes (1024+) preservan la coherencia semántica. En documentos con estructura explícita, esa
tensión se puede **esquivar** en lugar de arbitrar: el propio documento ya indica dónde están los
límites semánticos.

## Decisión

`build_chunks()` agrupa por **sección lógica** (`semantics.section` del contrato canónico), no por
longitud. Reglas:

1. La unidad de agrupación es la sección (`datos_solicitante`, `alegaciones`, `consentimiento`,
   `certificaciones`, `cierre`…), tal como la marcó el normalizador.
2. Un bloque de tipo `table`, `signature` o `stamp` **nunca** se parte.
3. Cada chunk arrastra metadata completa de trazabilidad:
   `document_id` · `page_number` · `block_id` · `block_type` · `bbox` · `section` · `entity_type?`

Esa metadata no es decorativa: es lo que permite al agente (ADR-003) anclar cada evidencia a un
bloque, una página y unas coordenadas concretas.

## Consecuencias

**Positivas**
- Los pares etiqueta–valor de los formularios sobreviven intactos a la indexación.
- El grounding espacial es directo: recuperar un chunk ya devuelve su `bbox`.
- Se elimina el hiperparámetro `chunk_size`, que en el enfoque clásico es un compromiso arbitrario
  y dependiente del corpus.
- Da a H2 un contraste limpio y medible: mismo pipeline, mismo agente, mismo juez, y como única
  variable el chunker (layout-aware vs. texto plano troceado a longitud fija).

**Negativas / coste asumido**
- El tamaño de chunk resulta **variable y no acotado**: una sección larga puede producir un chunk
  grande y diluir la señal del embedding. Mitigación prevista si aparece: subdividir por bloques
  dentro de la sección, manteniendo la restricción de no partir tabla/firma/sello.
- Depende críticamente de que el normalizador etiquete bien `semantics.section`. Un fallo aguas
  arriba degrada el chunking sin error visible.
- No es trasladable a corpus sin estructura (prosa libre, correos), donde el troceado clásico sigue
  siendo la opción correcta.

## Alternativas consideradas y descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Troceado por longitud fija con solapamiento | Rompe pares etiqueta–valor y tablas; es exactamente el baseline contra el que H2 se contrasta |
| Chunking semántico por similitud entre frases | Coste computacional adicional para reconstruir una estructura que el documento **ya declara** explícitamente |
| Un chunk por documento completo | Señal de embedding demasiado diluida; el `top_k` deja de discriminar entre requisitos |
| Un chunk por bloque individual | Fragmenta en exceso: pierde el contexto de sección que el juez necesita para valorar la evidencia |

## Nota sobre el modo demo

El fallback `naive_retriever.py` (solapamiento léxico tipo Jaccard) **conserva la misma estructura
de chunks**: solo cambia la función de puntuación, no la unidad indexada. Por eso la demo sin
dependencias pesadas sigue siendo representativa de la arquitectura real (ver ADR-005).

## Referencias

- `04_src/rag/chunking.py`, `04_src/rag/index_store.py`
- `04_src/ui/naive_retriever.py`
- `tests/rag/test_chunking.py` (6/6)
- Memoria, §"Modos de fallo del RAG clásico y estrategias de mitigación"

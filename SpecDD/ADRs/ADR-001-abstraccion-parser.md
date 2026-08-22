# ADR-001 · Abstracción del parser con backends intercambiables

**Estado:** Aceptada
**Fecha:** Junio 2026 (Fase 1)
**Decisores:** Fer (autor), asistido por Claude
**Requisitos afectados:** REQ-1.1, REQ-1.2, REQ-1.3

---

## Contexto

El proyecto necesita convertir documentos administrativos escaneados (PDF, imágenes) en una
representación estructurada con bloques, texto y coordenadas. El estado del arte ofrece varias
familias de modelos VDU / OCR-free con perfiles muy distintos:

| Opción | Tamaño | Requisito de cómputo | Calidad (benchmark propio de Datalab) |
|---|---|---|---|
| Chandra OCR-2 (pesos abiertos) | 4B | GPU necesaria | 85.9 |
| API gestionada de Datalab | — | Ninguno (red) | 86.7 |
| dots.ocr | ligero | GPU modesta | menor, más rápido |
| Nemotron-Parse 1.1 | ultraligero | CPU viable | referencia de producción |
| Donut / Pix2Struct | clásico | GPU | baseline histórico |

Restricción dura del proyecto: **el entorno de desarrollo solo dispone de CPU**. Chandra OCR-2 (4B)
es inviable en CPU para una demo interactiva.

Además, uno de los objetivos experimentales del TFM es precisamente **comparar** backends
(calidad vs. latencia vs. coste), lo que exige poder intercambiarlos sin reescribir el sistema.

## Decisión

Se define una **interfaz abstracta `DocumentParser`** con un único método `parse()`, más una
**factory `get_parser(backend=...)`**. Cada backend concreto es un adaptador independiente:

- `datalab_client.py` → API gestionada de Datalab (backend por defecto en desarrollo)
- `chandra_hf_client.py` → pesos abiertos vía Hugging Face (stub, para la comparativa futura)
- (previsto) `dotsocr_client.py`, `nemotron_client.py`

Todos devuelven el mismo tipo `ParserResult`, y **ninguno** conoce el esquema canónico:
la traducción a `CanonicalDocumentParse` es responsabilidad exclusiva del normalizador (ver ADR-002).

## Consecuencias

**Positivas**
- Cambiar de backend es un parámetro, no un refactor. Los tests aguas abajo no se tocan.
- Permite la comparativa *hospedado vs. open-weights* que el TFM necesita defender.
- Los tests unitarios mockean la interfaz, no el SDK de Datalab → suite rápida y sin red.
- `ParserResult` captura `elapsed_seconds`, `quality_score` y `cost_breakdown`, que alimentan
  directamente las métricas de eficiencia del capítulo de evaluación.

**Negativas / coste asumido**
- Una capa de indirección más, con su propio contrato que mantener.
- El campo `raw` es deliberadamente heterogéneo (varía por backend); el normalizador debe
  tener un adaptador de mapeo por cada uno.

**Riesgo documentado (honestidad académica)**
La API gestionada de Datalab **no es** literalmente "Chandra OCR-2 con pesos abiertos": es un
servicio propietario que ejecuta internamente una versión mejorada (86.7 vs. 85.9). Usarla es
coherente con la decisión práctica de "API externa durante el desarrollo", pero **debe declararse
explícitamente en la memoria** para no contradecir la narrativa open-source del capítulo de
herramientas. La mitigación prevista es una pasada final con pesos abiertos, o documentarlo como
variante de despliegue en trabajo futuro.

## Alternativas consideradas y descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Acoplar el código directamente al SDK de Datalab | Impide la comparativa entre modelos, que es un objetivo central del TFM |
| Ejecutar Chandra OCR-2 localmente desde el principio | Inviable: solo hay CPU disponible; la demo sería inutilizable |
| Usar un OCR clásico (Tesseract) como base | Pierde la información de layout y estructura, que es justo la aportación de los modelos VDU |
| Adoptar directamente el formato nativo de Marker como contrato interno | Acopla todo el sistema a un proveedor; ver ADR-002 |

## Referencias

- `04_src/parser/base.py`, `datalab_client.py`, `chandra_hf_client.py`
- `04_src/parser/quickstart_datalab_chandra.py` (mini-ejemplo autocontenido, REQ-1.4)
- Hilo 02 — decisión "no acoplar el sistema al formato nativo de ningún parser"

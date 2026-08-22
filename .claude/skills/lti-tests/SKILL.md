---
name: lti-tests
description: Genera o mejora tests unitarios para los módulos del pipeline de bastanteo (parser, normalizer, rag, agent, ui), priorizando casos borde y manejo de errores, siguiendo el estilo pytest ya establecido en tests/. Úsala cuando el usuario ejecute `/lti-tests` (opcionalmente indicando el módulo o fichero objetivo).
---

# lti-tests

> **Nota de nomenclatura:** el comando se llama `/lti-tests` por herencia de la plantilla base del
> framework (`claude-framework/COMMANDS.md`), pero este proyecto **no** tiene módulo LTI ni
> inserción de candidatos. Aplícalo siempre a los módulos reales del pipeline de bastanteo:
> `04_src/{parser,normalizer,rag,agent,ui}`.

Genera o mejora tests unitarios para un módulo o función del proyecto, con foco en **casos borde y
manejo de errores**, manteniendo consistencia con la suite existente (36 tests en verde a fecha de
la última revisión de `SpecDD/03-Component-Specs.md`).

## Activación

- `/lti-tests` sin argumento → pregunta primero qué módulo o fichero cubrir (no adivines; los
  módulos tienen contratos y invariantes específicos documentados en `SpecDD/03-Component-Specs.md`
  que no debes violar por accidente).
- `/lti-tests <módulo o ruta>` → genera/mejora tests directamente para ese objetivo.

## Antes de escribir nada

1. Lee el código fuente del módulo objetivo en `04_src/<módulo>/`.
2. Lee el fichero de test existente en `tests/<módulo>/` si ya existe — la coherencia con lo que
   hay pesa más que la perfección aislada de un test nuevo.
3. Si el módulo tiene contrato en `SpecDD/03-Component-Specs.md` (C1–C5), léelo: invariantes,
   estructura de errores y campos obligatorios deben quedar cubiertos por al menos un test.

## Convenciones de estilo (derivadas de la suite existente, ej. `tests/agent/test_bastanteo.py`)

- Funciones sueltas `def test_<acción>_<condición>_<resultado_esperado>():`, **sin clases** de test.
- Arrange-Act-Assert implícito, sin comentarios `# Arrange` / `# Act` — el propio nombre de la
  función y la separación en bloques ya lo comunican.
- Fakes/fixtures locales como funciones auxiliares con prefijo `_` (p. ej. `_fake_retrieve_fn`),
  no mocks de librerías salvo que el módulo llame a una API externa real (ver `tests/parser/` para
  el patrón de mocks del SDK de Datalab).
- Asserts directos y específicos; evita `assert result` genérico cuando puedes comprobar el campo
  concreto (`result["bastanteo_gold"]["status"] == "VALIDO"`).
- Nombres de fixtures/datos de ejemplo en el dominio del proyecto (DNI, expediente, documento,
  bastanteo, evidencia) — no genéricos tipo `foo`/`bar`.

## Qué priorizar

1. **Casos borde reales del dominio**, no genéricos: requisito `optional` ausente, `citations`
   vacías, score justo en el umbral, `contradicted` vs `missing`, campos `None` en `ParserResult`.
2. **Manejo de errores documentado en el contrato**: si `SpecDD/03-Component-Specs.md` lista una
   excepción (`ValueError`, `RuntimeError`, `jsonschema.ValidationError`...), debe existir un test
   que la dispare y verifique el mensaje o el tipo.
3. **Invariantes explícitos** de la spec (p. ej. "el agente nunca infiere evidencia no recuperada"
   en C4) — estos son los tests de mayor valor porque protegen la propiedad más crítica del sistema
   (no-alucinación), no solo la sintaxis del código.
4. No dupliques cobertura ya existente — si un caso ya está testeado, mejóralo en vez de repetirlo.

## Ubicación

- Fichero nuevo: `tests/<módulo>/test_<algo_descriptivo>.py`, reflejando el mismo nombre de módulo
  que `04_src/<módulo>/`.
- Fichero existente: añade funciones al final, respetando el orden temático ya presente.

## Tras generar los tests

- Ejecuta (o indica al usuario que ejecute) `pytest tests/<módulo>/ -q` y reporta el resultado.
- Si el módulo depende de librerías pesadas no instaladas (`chromadb`, `llama-index` — ver
  `tests/rag/test_index_store.py`), usa `pytest.skip()` con el motivo, como ya se hace allí; no
  falles la suite por una dependencia opcional.
- Si el test revela una discrepancia entre el código y el contrato de `SpecDD/03-Component-Specs.md`
  (como los bugs reales ya documentados: `quality_score` fuera de rango, `Judge` abstracto mal
  instanciado, `ImportError` no capturado), repórtalo explícitamente al usuario en vez de "arreglarlo"
  en silencio — puede ser una decisión de diseño pendiente de discutir, no solo un bug.

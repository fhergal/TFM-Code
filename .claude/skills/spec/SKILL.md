---
name: spec
description: Genera o refina especificaciones técnicas SpecDD (entradas, salidas, contratos, invariantes, errores) para los componentes del sistema (parser, normalizer, rag, agent, ui), manteniendo el formato y la numeración C1-C5 de SpecDD/03-Component-Specs.md. Úsala cuando el usuario ejecute `/spec` (indicando el componente o cambio a especificar).
---

# spec

Genera o refina especificaciones técnicas para un componente del pipeline de bastanteo, integrándolas
en `SpecDD/03-Component-Specs.md` con el mismo formato que los componentes C1–C5 ya documentados.

## Activación

- `/spec <componente o C#>` → refina la spec existente de ese componente (p. ej. `/spec C3` o
  `/spec rag`).
- `/spec <descripción de algo nuevo>` → propone una spec nueva para funcionalidad que aún no tiene
  contrato formal; pregunta primero a qué componente existente pertenece o si merece uno nuevo (C6+).
- Sin argumento → pregunta qué componente o cambio se va a especificar antes de escribir nada.

## Principio rector del proyecto (no lo rompas)

> Todo módulo se comunica con el resto **exclusivamente** a través del contrato
> `CanonicalDocumentParse v1.1` (`specs/canonical_document_parse.schema.json`) o de tipos derivados.
> Ningún componente aguas abajo debe conocer el formato nativo de otro aguas arriba.

Antes de proponer cualquier interfaz nueva, comprueba que no la viola (consulta la "Matriz de
acoplamiento" al final de `SpecDD/03-Component-Specs.md`).

## Antes de escribir

1. Lee `SpecDD/03-Component-Specs.md` completo — la spec nueva debe encajar con las existentes
   (mismo componente vecino aguas arriba/abajo, mismos tipos de campo, mismo vocabulario cerrado
   donde aplique, p. ej. `block_type` en C2).
2. Lee el código real del módulo en `04_src/<módulo>/` — la spec describe el contrato **real**, no
   uno aspiracional; si el código diverge de una spec existente, señala la discrepancia en vez de
   ocultarla.
3. Si el cambio afecta a `specs/canonical_document_parse.schema.json`, indícalo explícitamente y
   pregunta si corresponde también actualizar el schema (son dos ficheros distintos que deben ir
   sincronizados).
4. Revisa `SpecDD/02-Requisitos.md` para enlazar la spec con su(s) requisito(s) `REQ-X.Y`.

## Estructura obligatoria por componente (igual que C1–C5 existentes)

```markdown
## C<n> · <Nombre del componente>

**Módulo:** `04_src/<ruta>/` (ficheros)
**Requisitos cubiertos:** REQ-X.1 … REQ-X.N

### Interfaz
(firma de funciones/clases en Python, con type hints)

### Contrato
| | Descripción |
|---|---|
| **Entrada** | ... |
| **Salida** | ... |
| **Efectos** | red / disco / ninguno (función pura) |

### Estructura de <tipo de salida> (si aplica)
(tabla de campos: nombre, tipo, obligatorio, notas)

### Invariantes
(propiedades que SIEMPRE se cumplen — las más importantes primero, en negrita si son críticas
para el sistema, como el invariante de no-alucinación de C4)

### Errores
| Excepción | Causa |
|---|---|
```

## Reglas de contenido

- **Invariantes antes que features**: el invariante de no-alucinación de C4 es el ejemplo a seguir
  — no describas solo qué hace el componente, describe qué **nunca** debe hacer.
- Si un bug real ya se detectó y corrigió durante el desarrollo (como `quality_score` fuera de
  rango o el `ImportError` no capturado en C5), consérvalo como nota entre paréntesis en la spec:
  documenta la razón de ser de la restricción, no solo la restricción.
- Vocabulario cerrado (enums de `block_type`, `status`, `requirement_type`...) se define **una
  única vez** en la spec del componente que lo origina; los demás componentes lo referencian, no
  lo redefinen.
- Actualiza la "Matriz de acoplamiento" y la tabla "Cobertura de tests por componente" al final del
  fichero si el cambio afecta a quién conoce a quién o a qué tests cubren el componente.
- Si la spec implica una decisión de diseño con alternativas descartadas (no solo un contrato), no
  la metas en `03-Component-Specs.md`: propón un ADR nuevo en `SpecDD/ADRs/` siguiendo el formato de
  los 5 existentes, y enlázalo desde `SpecDD/README.md`.

## Tras generar/refinar la spec

- Señala explícitamente si el código actual en `04_src/` ya cumple el contrato, lo cumple
  parcialmente, o aún no existe (spec-first).
- Si detectas que la spec obliga a cambiar tests existentes en `tests/<módulo>/`, dilo — no los
  cambies tú mismo salvo que el usuario lo pida (usa `/lti-tests` para eso).

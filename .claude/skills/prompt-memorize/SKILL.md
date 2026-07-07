---
name: prompt-memorize
description: Activa el modo de memorización de prompts para la sesión actual. A partir de su activación, registra de forma literal cada prompt del usuario y cada respuesta de Claude en un archivo Markdown `prompts-ARP.md`. Úsala cuando el usuario ejecute `/prompt-memorize` (opcionalmente con `--include-all` para incluir también los prompts anteriores de la sesión).
---

# prompt-memorize

Activa el modo de memorización de prompts para la sesión actual. Cada prompt del usuario y cada respuesta de Claude se registran de forma **literal y exacta** en un archivo Markdown llamado `prompts-ARP.md`.

## Activación

- `/prompt-memorize` → comienza a registrar **desde el siguiente prompt** en adelante (no incluye los anteriores).
- `/prompt-memorize --include-all` → registra **todos los prompts de la sesión**, incluyendo los anteriores al comando, comenzando desde el primero en orden cronológico.

## Ubicación del archivo

Determina la ruta destino en este orden:

1. Si hay un proyecto abierto en la sesión, crea/usa `prompts-ARP.md` en la **raíz del proyecto** (el directorio de trabajo principal de la sesión).
2. Si no hay proyecto abierto, créalo en el **directorio de trabajo actual**: `./prompts-ARP.md`.
3. Si el archivo ya existe, **anexa** los nuevos registros al final (no sobreescribas). Si no existe, créalo automáticamente.

## Reglas de registro

- Copia el contenido de cada prompt y cada respuesta de forma **literal y exacta**: no parafrasees, no resumas, no corrijas ni modifiques nada.
- La numeración de prompts es **secuencial y continua** durante toda la sesión (no se reinicia al activar el comando).
- Con `--include-all`, los prompts anteriores al comando se numeran desde `1` en orden cronológico.
- El comando `/prompt-memorize` en sí **no se registra** como prompt en el archivo.
- El modelo de IA se indica con el nombre exacto del modelo activo en la sesión (p. ej. `Opus 4.8`, `Sonnet 4.6`).
- Mantén el registro actualizado: tras cada nuevo intercambio (prompt + respuesta), añade su bloque correspondiente al archivo.

## Estructura del archivo `prompts-ARP.md`

Cada intercambio se registra con este formato exacto:

```markdown
## Prompt {numero_de_prompt}
{prompt_enviado_literal}

## Respuesta Prompt {numero_de_prompt} Claude (modelo {modelo_IA})
{respuesta_literal}
---
```

### Ejemplo

```markdown
## Prompt 1
¿Cómo me llamo?

## Respuesta Prompt 1 Claude (modelo Sonnet 4.6)
Tu nombre es Angel
---

## Prompt 2
¿Cuántos años tengo?

## Respuesta Prompt 2 Claude (modelo Sonnet 4.6)
No tengo información sobre tu edad, no me la has dicho.
---
```

## Mensaje de confirmación

Al activar el comando, responde con un mensaje corto indicando desde qué número de prompt comenzará a registrar:

```
✅ Modo prompt-memorize activado. Registrando desde el prompt #N en: {ruta_raiz_proyecto}/prompts-ARP.md
```

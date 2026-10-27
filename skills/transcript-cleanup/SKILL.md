---
name: transcript-cleanup
description: Transcribe audio o video con Deepgram Nova-3 y produce un .docx limpio, fiel a lo dicho, con marcas de tiempo reales — para entrevistas, talleres, paneles o cualquier grabación que necesite pasar de audio crudo a transcripción de revisión. Úsalo cuando el usuario pida transcribir un audio, limpiar una transcripción existente, procesar un JSON de Deepgram, revisar o resolver los tramos [dudoso]/[inaudible] escuchando clips, o cuando Deepgram/nova-3 no esté detectando habla en una grabación (volumen bajo, eco, mala calidad).
---

# Transcript cleanup — pipeline genérico

Convierte audio (o un JSON de Deepgram ya generado) en una transcripción `.docx` fiel a lo
dicho, con marcas de tiempo reales por turno. Sirve para un caso suelto o para una serie de
entrevistas del mismo proyecto. No asume un glosario ni un dominio fijo — eso vive en la config
de cada proyecto (ver "Config por proyecto" abajo), no en este skill.

## Principios (no negociables)

1. **No inventar.** Si un tramo no se entiende, marcar `[inaudible]`; si es probable pero no
   seguro, `[dudoso: hipótesis]`. Nunca rellenar con texto plausible. Dar siempre el
   **timestamp exacto** del tramo dudoso (no aproximado) — así se puede ubicar y confirmar
   contra el audio si alguien lo escucha después.
2. **Fidelidad sobre pulido.** Corregir errores del ASR y puntuación; conservar cómo habla la
   persona (muletillas, regionalismos, disfluencias reales). No reescribir ni "mejorar" el
   discurso.
3. **Construir desde el JSON, nunca alinear.** Armar la transcripción directo de Deepgram
   (`utterances` o `words`, ver Paso 2). No alinear un texto ya limpio contra el JSON — eso
   rompe timestamps y atribución de hablante.
4. **Confianza del ASR ≠ solo error de palabra.** Un tramo raro puede ser una palabra mal
   transcrita, pero también un cambio de hablante que la diarización no detectó. Si la
   confianza de hablante es baja o hay pocos cambios de hablante para la duración del audio,
   considerar esa hipótesis también antes de asumir que es un garble.
5. **Estandarizar con criterio, no a ciegas.** Un término mal transcrito de forma consistente
   (variantes fonéticas del mismo nombre/organización) se puede corregir sin `[dudoso]` si el
   contexto interno de la misma grabación lo confirma (se repite, o se dice completo en algún
   punto). Si es una sola mención con confianza baja y sin refuerzo interno, dejar `[dudoso]`.
6. **La confirmación humana manda.** Si quien encargó el trabajo escucha el audio y corrige
   algo, esa corrección es verdad, no una hipótesis más.
7. **Medir dos veces.** En un lote de varias grabaciones, procesar y mostrar una completa antes
   de escalar a las demás — sobre todo si es la primera vez que se usa este skill en un proyecto
   nuevo (glosario, convención de etiquetas, etc. aún no calibrados).

## Flujo

```
audio.mp3/.m4a ──(transcribe.sh)──> <id>_deepgram.json
   ──(diagnose_audio.sh, si hace falta)──> audio normalizado ──> re-transcribir
   ──(build_turns.py y/o build_turns_words.py)──> merged.json / merged_words_<id>.json
   ──(limpieza fina, criterio de lenguaje)──> turns_ts.json + cfg.json
   ──(find_dudosos.py + make_clips.py)──> dudosos.json + clips_dudosos/
   ──(revisión escuchando: review_server.py | selector en la CLI)──> resoluciones.json
   ──(apply_resoluciones.py)──> turns_ts.json + cfg.pendientes actualizados
   ──(build_transcript.js)──> <id>_transcripcion.docx
```

### Paso 0 — Transcribir

```bash
export DEEPGRAM_API_KEY=...   # o dejarlo en un .env que el usuario indique
scripts/transcribe.sh /ruta/a/audios              # todos los audios de la carpeta
scripts/transcribe.sh /ruta/a/audios archivo.mp3  # uno solo
```

Acepta también video (`.mp4/.mov/.mkv/.webm`): extrae solo el audio con ffmpeg antes de enviarlo.
Anotar la ruta del archivo original (audio o video) en `media` de `cfg.json` — la usa el Paso 2.5
para cortar los clips.

Usa `model=nova-3&detect_language=true&diarize=true&utterances=true&utt_split=0.8&smart_format=true&punctuate=true`
por defecto. Si el proyecto tiene keyterms de dominio (nombres propios poco comunes, máximo
~100 términos), agregarlos con `&keyterm=...` — mejora el reconocimiento; no cargar de más
(empeora los resultados). No usar `redact=pii`: sobre-redacta y deja el contenido inservible;
la tokenización de personas (si el proyecto la requiere) se hace en la limpieza fina, a mano.

**Antes de dar por buena una transcripción de un archivo largo (>15-20 min), correr el
diagnóstico del Paso 0.5.**

### Paso 0.5 — Diagnóstico de calidad de audio

```bash
scripts/diagnose_audio.py <id>_deepgram.json
```

Calcula palabras/minuto y reporta huecos de silencio >30s. Una conversación normal ronda
100-150 palabras/min.

- **Si la densidad es muy baja y hay huecos largos de silencio:** probable problema de volumen,
  no de contenido. Probar:
  ```bash
  ffmpeg -i audio.mp3 -af volumedetect -f null -   # mean_volume muy negativo (< -25dB) confirma
  ffmpeg -i audio.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 16000 -ac 1 -c:a <mismo formato> salida.mp3
  ```
  Probar primero en un fragmento de 60-90s tomado de una zona sin habla detectada — mucho más
  barato que reprocesar el archivo completo, y confirma la hipótesis rápido. Si funciona,
  normalizar el archivo completo y volver a transcribir (Paso 0), guardando el JSON original
  como backup (`<id>_deepgram_ORIGINAL_backup.json`) antes de sobrescribir.
- **Si nova-3 devuelve confianza 0.0 en varios puntos del archivo incluso ya normalizado,
  con denoise, y exportado a WAV sin comprimir:** no es un problema de volumen ni de mi
  pipeline — el modelo está rechazando el audio por completo (típico de eco/reverberación
  fuerte, voces a muy distinta distancia del micrófono, o solapamiento constante de hablantes).
  Cruzar con Whisper (mismo endpoint de Deepgram, sin cómputo local) sobre un fragmento corto:
  ```bash
  curl ... "https://api.deepgram.com/v1/listen?model=whisper-large&language=<idioma>&smart_format=true&punctuate=true"
  ```
  Si Whisper sí saca algo (aunque parcial), confirma que hay habla real y el problema es
  específico de nova-3 con esa acústica. **Whisper alucina texto repetitivo en tramos poco
  claros — no es un reemplazo confiable de nova-3.** Es un último recurso que necesita revisión
  humana pesada, no limpieza fina automática. Avisar esto explícitamente antes de usarlo sobre
  un archivo completo; no presentar su salida como transcripción lista para limpieza ligera.
  El gateway de Deepgram corta requests síncronos largos con `whisper-large` — si hay que
  procesar un archivo completo, fragmentar en trozos de ~5 min y unir después.
- Si ninguna de las dos aplica, no forzar nada: puede ser una grabación genuinamente corta o
  con silencios reales (pausas, actividad no verbal).

### Paso 1 — Construir los turnos

Probar ambos métodos y comparar el número de turnos resultante:

```bash
python scripts/build_turns.py <id>_deepgram.json merged.json
python scripts/build_turns_words.py <id>_deepgram.json merged_words_<id>.json
```

- `build_turns.py` agrupa por `utterances` (ya viene agrupado por Deepgram con `utt_split`).
- `build_turns_words.py` agrupa por el `speaker` de cada palabra individual — más lento de
  generar pero más fino.

**Si el conteo de turnos por palabra es notablemente mayor que por utterance**, es señal de que
`utterances` está fusionando intervenciones cortas de un hablante distinto (interjecciones,
confirmaciones breves, preguntas cortas) dentro del turno largo de otro hablante — común en
audio de un solo micrófono o con un hablante que domina la conversación. Usar la versión por
palabra como base de `turns_ts.json` en ese caso; puede incluso recuperar frases completas que
la versión por utterance pierde del todo. Si ambos métodos dan el mismo número de turnos, no
hace falta reconstruir nada especial.

**Etiquetas de hablante:** si ya existe una convención establecida para ese archivo (limpieza
previa), preservarla al reconstruir — no reasignar solo porque el orden de primera aparición
cambió. Si es la primera pasada, asignar por orden de primera aparición. Si un nombre real se
confirma (contexto fuerte o lo dice quien encargó el trabajo), usarlo en vez de una etiqueta
genérica.

### Paso 2 — Limpieza fina (la parte que necesita criterio; el skill la sistematiza, no la vuelve automática)

Sobre cada turno crudo: aplicar los principios de arriba, el glosario del proyecto si existe
(ver `references/criterios-limpieza-ejemplo.md` para el formato sugerido), y marcar
`[dudoso]`/`[inaudible]` donde aplique. Guardar como `turns_ts.json`: lista de objetos
`{i, label, ts, text}`, o `{label, ts: null, text, note: true}` para notas de revisión que se
muestran en rojo/itálica en el documento.

### Paso 2.5 — Revisión de dudosos escuchando los clips

Cuando la limpieza fina deja marcas `[dudoso...]` / `[inaudible]`, ofrecer al usuario revisarlas
escuchando: un clip por tramo, opciones razonadas, y elige (o escribe otra). Si no quiere revisar
ahora, saltar al Paso 3 — las marcas quedan como pendientes, como siempre.

1. **Ubicar los tramos:**
   ```bash
   python scripts/find_dudosos.py <dir> <id>_deepgram.json
   ```
   Escribe `<dir>/dudosos.json` con `start`/`end` estimados (ventana del turno + palabras de
   confianza baja más cercanas a la marca) y el texto ASR crudo de cada tramo con su confianza.
   Revisar que `asr` corresponda a lo marcado; si no, corregir `start`/`end` a mano con las
   `words` del JSON de Deepgram.
2. **Redactar las opciones** de cada entrada (`opciones`: lista de 1-3 textos), editando
   `dudosos.json`. Cada opción tiene que tener apoyo concreto: el ASR crudo, una variante
   fonética de él, un término del glosario del proyecto, o algo que se dice en otra parte de
   la misma grabación. Ordenar de más a menos probable. **No inventar opciones plausibles sin
   apoyo** (principio 1) — si solo hay una hipótesis razonable, dar solo esa. `[inaudible]` y
   "dejar como está" se ofrecen siempre aparte; no meterlos en `opciones`.
3. **Cortar los clips:**
   ```bash
   python scripts/make_clips.py <dir>            # usa `media` de cfg.json
   python scripts/make_clips.py <dir> video.mp4  # o la ruta explícita
   ```
   `clips_dudosos/<id>_<HHMMSS>.mp3`, o `.mp4` con imagen si la fuente es video (`--audio-only`
   para forzar audio). Cada clip trae 1.5 s antes y 1 s después del tramo. Volver a correr
   este paso si cambian las opciones (regenera `clips_dudosos/index.md`).
4. **Revisar — según dónde corre la sesión:**
   - **App Desktop (pestaña Code)** — si están disponibles las herramientas del navegador
     integrado (`mcp__Claude_Browser__*`): levantar el servidor **en segundo plano**
     ```bash
     python scripts/review_server.py <dir>        # http://127.0.0.1:8765/ ; --port si está ocupado
     ```
     y abrir esa URL en el panel del navegador de la app. La página muestra un reproductor por
     tramo, las opciones, `[inaudible]`, "dejar como está" y un campo "Otra opción". Cada
     elección se guarda al momento en `resoluciones.json`. Esperar a que el usuario diga que
     terminó (botón «Terminé», que además apaga el servidor). Solo escucha en 127.0.0.1: el
     audio no sale de la máquina. No publicar los clips en ningún servicio externo.
   - **Terminal (CLI)** — decir la ruta de `clips_dudosos/` (con `index.md`) y cómo abrirla
     (`start` en Windows, `open` en macOS, `xdg-open` en Linux). Luego preguntar con el selector
     de preguntas (AskUserQuestion) **en lotes de 4 tramos** (el máximo por llamada), en orden:
     - `header`: el id (`d01`); `question`: timestamp, nombre del clip y el contexto corto con
       la marca, p. ej. *«[00:12:41] d03_001241.mp3 — "…de la cooperativa ___ y de cómo
       empezó…" ¿Qué se dice?»*
     - `options`: las de `opciones` (máx. 3) + `[inaudible]` (2-4 en total). Si no hay
       `opciones`, ofrecer `[inaudible]` y "Dejar como está". "Otro" lo agrega el selector solo:
       es el texto libre del usuario.
     - Tras cada lote, escribir las respuestas en `resoluciones.json` (formato abajo, `via:
       "cli"`) antes de seguir con el siguiente.
   Formato de `resoluciones.json` (igual en ambos modos):
   `{"d01": {"eleccion": "opcion"|"otro"|"inaudible"|"mantener", "texto": "...", "via": "pagina"|"cli", "fecha": "ISO"}}`.
   Un tramo sin entrada cuenta como "mantener".
5. **Aplicar:**
   ```bash
   python scripts/apply_resoluciones.py <dir>
   ```
   Reemplaza cada marca por lo elegido (respaldo en `turns_ts.before_review.json`) y deja rastro
   en `cfg.json → pendientes`: lo confirmado con su timestamp, y lo no resuelto como pendiente.
   Lo que elige el usuario es confirmación humana (principio 6): va al texto sin `[dudoso]`.
   Se puede volver a correr sin duplicar nada.

### Paso 3 — cfg.json y el documento

Config por grabación (ver `assets/cfg.example.json`):
`{id, archivo, media, idioma, duracion, hablantes, notas, pendientes}`. El **id controla** el nombre
de archivo de salida desde una sola fuente. Sin `\n` en `notas` — el generador no convierte
saltos de línea. `pendientes` se genera de lo que de verdad quedó abierto en *esa* grabación —
no heredar una lista fija de otro proyecto. Cada estandarización o `[dudoso]` debe dejar rastro
ahí con su timestamp.

```bash
node scripts/build_transcript.js /ruta/al/directorio/de/la/grabacion
```

Lee `cfg.json` + `turns_ts.json` de ese directorio, escribe `<id>_transcripcion.docx` ahí mismo.
Estructura del documento: título, metadatos, notas del archivo (si hay), transcripción
(`Hablante N [HH:MM:SS]: texto`, o `Entrevistador/R` si el proyecto lo prefiere — configurable
en `cfg.json`/el propio script), y notas/pendientes de revisión al final.

## Config por proyecto (lo que NO vive en este skill)

Cada proyecto que use este skill trae su propio:
- **Glosario de dominio** (nombres de organizaciones, personas, términos técnicos recurrentes)
  — ver `references/criterios-limpieza-ejemplo.md` para el formato.
- **Convención de etiquetas de hablante** (`Hablante 1/2`, `Entrevistador(a)/R`, nombres reales).
- **Política de datos sensibles** (tokenizar nombres de personas o no; qué se conserva en claro).

No mezclar el glosario/criterios de un proyecto con otro. Si dos proyectos resultan ser la
misma red o tema (pasa más seguido de lo que parece — revisar si términos/nombres se repiten
entre grabaciones de "proyectos" distintos antes de asumir que no tienen relación), documentarlo
explícitamente en vez de fusionar sus configuraciones.

## Qué NO hacer

- No alinear un texto ya "limpio" contra el JSON — arma siempre los turnos directo del JSON.
- No usar `redact=pii` de Deepgram.
- No forzar una corrección sin apoyo contextual solo para "limpiar" el `[dudoso]`.
- No presentar una salida de Whisper (fallback de audio difícil) como transcripción lista para
  limpieza ligera — es un borrador crudo que necesita revisión pesada.
- No escalar a un lote completo de grabaciones sin validar el criterio en al menos una primero.
- No subir clips de las grabaciones a servicios externos (Artifacts, Drive, etc.) para la
  revisión de dudosos: se revisan en local.

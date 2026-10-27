# transcript-cleanup-toolkit

Plugin de [Claude Code](https://claude.com/claude-code) para transcribir audio (entrevistas,
talleres, paneles) con [Deepgram](https://deepgram.com) Nova-3 y producir un `.docx` de
revisión, limpio y fiel a lo dicho, con marcas de tiempo reales por turno.

Nació de procesar varias series de entrevistas reales (de campo, telefónicas, paneles
multihablante) y toparse siempre con los mismos problemas: Deepgram fusiona intervenciones
cortas de un hablante dentro del turno de otro, el volumen bajo hace que no detecte habla en
tramos enteros, y el eco/reverberación puede tumbar la confianza del modelo a cero en un
archivo completo. Este skill sistematiza cómo diagnosticar y resolver esos casos antes de
invertir tiempo en limpieza fina de texto.

## Qué incluye

- **`skills/transcript-cleanup/`** — el skill: `SKILL.md` con el flujo completo y los
  principios de limpieza (no inventar, `[dudoso]`/`[inaudible]`, fidelidad sobre pulido), más:
  - `scripts/transcribe.sh` — llama a Deepgram (nova-3, diarización, detección de idioma).
  - `scripts/diagnose_audio.py` — chequeo de densidad de palabras/huecos de silencio, para
    detectar problemas de volumen antes de limpiar.
  - `scripts/build_turns.py` / `build_turns_words.py` — arman los turnos desde el JSON crudo,
    por *utterance* o por palabra (esta última resuelve diarización floja en audio de un solo
    micrófono o con un hablante dominante).
  - `scripts/find_dudosos.py` / `make_clips.py` — ubican en el tiempo cada `[dudoso]`/`[inaudible]`
    y cortan un clip de cada uno (mp3, o mp4 con imagen si la fuente es video).
  - `scripts/review_server.py` + `assets/review.html` — página local para escuchar cada clip y
    elegir la opción correcta o escribir otra (en la app Desktop se abre en el panel del navegador).
    En la terminal, la misma revisión se hace en el chat, de 4 en 4 tramos.
  - `scripts/apply_resoluciones.py` — aplica las elecciones a `turns_ts.json` y a los pendientes.
  - `scripts/build_transcript.js` — genera el `.docx` final desde `cfg.json` + `turns_ts.json`.
  - `references/criterios-limpieza-ejemplo.md` — plantilla para el glosario/criterios propios
    de cada proyecto (esto vive en el proyecto que usa el skill, no en el skill).
  - `assets/cfg.example.json` — plantilla de config por grabación.

## Qué NO incluye (a propósito)

Ningún glosario de dominio, convención de etiquetas de hablante fija, ni política de
tokenización de nombres. Eso es config de cada proyecto — ver
`references/criterios-limpieza-ejemplo.md` para cómo documentarlo. El skill aporta el pipeline
mecánico y el árbol de decisión de calidad de audio; el criterio de limpieza fina de cada
grabación lo sigue poniendo quien la revisa.

## Manual

**[`manual-instalacion.pdf`](manual-instalacion.pdf)** — manual completo de instalación y uso
(19 pp.): instalación en la CLI y en la pestaña **Code** de la app Claude Desktop, cómo montar
el proyecto que va a usar el plugin, el flujo paso a paso (incluida la revisión de dudosos
escuchando los clips), el árbol de decisión de calidad de
audio, cómo se ha usado en proyectos reales y solución de problemas.

La fuente es `docs/manual.html`; se regenera con `python3 docs/build_manual.py` (requiere
`weasyprint`), o con `python3 docs/build_manual.py --chrome` (usa Chrome/Edge; sirve en Windows).

## Instalación (Claude Code)

```
/plugin marketplace add ramonzamora89/transcript-cleanup-toolkit
/plugin install transcript-cleanup-toolkit@transcript-cleanup-toolkit
```

En la **app Claude Desktop**, los mismos pasos van dentro de una sesión de la pestaña **Code**:
registrar el marketplace con `/plugin marketplace add ...` e instalar desde el botón **+** →
*Plugins* → *Add plugin*. El menú lateral *Customize → Plugins* es de las pestañas Chat y
Cowork: **no** alimenta las sesiones de Code. Y la clave de Deepgram hay que cargarla en el
editor de entorno local de la app —Desktop no lee los `export` del `.zshrc`—. Ver §4 del manual.

O clonar el repo y apuntar Claude Code a la carpeta localmente
(`claude --plugin-dir /ruta/local/transcript-cleanup-toolkit`).

## Requisitos

- `DEEPGRAM_API_KEY` en el entorno.
- `ffmpeg`/`ffprobe` (normalización de volumen, diagnóstico de eco, audio de videos y clips de dudosos).
- Python 3 y Node.js (con `npm install` dentro de `skills/transcript-cleanup/` para la
  dependencia `docx` que usa `build_transcript.js`).

## Uso típico

```bash
export DEEPGRAM_API_KEY=...
cd skills/transcript-cleanup
npm install

scripts/transcribe.sh /ruta/a/tus/audios
python scripts/diagnose_audio.py /ruta/a/transcripciones/<id>/<id>_deepgram.json
python scripts/build_turns_words.py /ruta/a/.../<id>_deepgram.json merged_words.json
# ... limpieza fina con criterio humano/Claude sobre merged_words.json -> turns_ts.json ...
python scripts/find_dudosos.py /ruta/.../<id> /ruta/.../<id>_deepgram.json
python scripts/make_clips.py /ruta/.../<id> /ruta/al/audio_o_video
python scripts/review_server.py /ruta/.../<id>      # o la revisión en el chat, desde la CLI
python scripts/apply_resoluciones.py /ruta/.../<id>
node scripts/build_transcript.js /ruta/a/transcripciones/<id>
```

Dentro de una sesión de Claude Code con este plugin instalado, basta con pedir "transcribe y
limpia esta entrevista" — el skill se activa solo y sigue el flujo descrito en `SKILL.md`.

## Licencia

MIT — ver `LICENSE`.

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

## Instalación (Claude Code)

```
/plugin marketplace add ramonzamora89/transcript-cleanup-toolkit
/plugin install transcript-cleanup-toolkit@transcript-cleanup-toolkit
```

O clonar el repo y apuntar Claude Code a la carpeta localmente.

## Requisitos

- `DEEPGRAM_API_KEY` en el entorno.
- `ffmpeg` (normalización de volumen, diagnóstico de eco).
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
node scripts/build_transcript.js /ruta/a/transcripciones/<id>
```

Dentro de una sesión de Claude Code con este plugin instalado, basta con pedir "transcribe y
limpia esta entrevista" — el skill se activa solo y sigue el flujo descrito en `SKILL.md`.

## Licencia

MIT — ver `LICENSE`.

#!/usr/bin/env bash
# Transcribe uno o varios audios (mp3/m4a/wav) con Deepgram (nova-3, detección automática de
# idioma). Omite archivos que ya tienen un JSON válido (sin err_code).
#
# Uso:
#   transcribe.sh <carpeta_audios> [<carpeta_salida>] [archivo1 archivo2 ...]
#
#   transcribe.sh ./audios                        # transcribe todos los audios de la carpeta
#   transcribe.sh ./audios ./transcripciones       # con carpeta de salida explícita
#   transcribe.sh ./audios ./transcripciones "Entrevista 1.m4a"   # uno solo, por nombre
#
# Requiere DEEPGRAM_API_KEY en el entorno (o en un .env que ya hayas cargado antes de llamar
# este script — este script no busca .env por vos, a propósito: la ruta de credenciales es
# distinta en cada máquina/proyecto).
#
# Opcional: KEYTERMS="término uno,término dos" para pasar keyterms de dominio a Deepgram
# (máximo ~100 términos cortos; cargar de más empeora los resultados).
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Uso: transcribe.sh <carpeta_audios> [<carpeta_salida>] [archivo1 archivo2 ...]" >&2
  exit 1
fi

AUDIOS_DIR="$1"; shift
OUT_ROOT="$AUDIOS_DIR/../transcripciones"
if [ "$#" -gt 0 ] && [ -d "$1" ]; then
  OUT_ROOT="$1"; shift
fi
mkdir -p "$OUT_ROOT"
OUT_ROOT="$(cd "$OUT_ROOT" && pwd)"

if [ -z "${DEEPGRAM_API_KEY:-}" ]; then
  echo "ERROR: DEEPGRAM_API_KEY no está definido en el entorno." >&2
  echo "  export DEEPGRAM_API_KEY=... (o cargar tu .env) antes de correr este script." >&2
  exit 1
fi

QS="model=nova-3&detect_language=true&diarize=true&utterances=true&utt_split=0.8&smart_format=true&punctuate=true"
if [ -n "${KEYTERMS:-}" ]; then
  IFS=',' read -ra TERMS <<< "$KEYTERMS"
  for t in "${TERMS[@]}"; do
    encoded="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1].strip()))" "$t")"
    QS="${QS}&keyterm=${encoded}"
  done
fi

slugify() {
  python3 -c "
import sys, unicodedata, re
s = sys.argv[1]
s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
s = s.lower()
s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
print(s)
" "$1"
}

content_type_for() {
  case "${1##*.}" in
    mp3|MP3) echo "audio/mpeg" ;;
    m4a|M4A|mp4|MP4) echo "audio/mp4" ;;
    wav|WAV) echo "audio/wav" ;;
    *) echo "audio/mpeg" ;;
  esac
}

transcribe_one() {
  local audio="$1"
  local base slug outdir json_out ext ctype
  base="$(basename "$audio")"
  base="${base%.*}"
  ext="${audio##*.}"
  slug="$(slugify "$base")"
  outdir="$OUT_ROOT/$slug"
  mkdir -p "$outdir"
  json_out="$outdir/${slug}_deepgram.json"
  ctype="$(content_type_for "$audio")"

  if [ -s "$json_out" ] && ! grep -q '"err_code"' "$json_out" 2>/dev/null; then
    echo "SKIP (ya existe): $base -> $json_out"
    return 0
  fi

  echo "Transcribiendo: $base -> $json_out"
  curl -sS -X POST \
    -H "Authorization: Token ${DEEPGRAM_API_KEY}" \
    -H "Content-Type: ${ctype}" \
    --data-binary "@${audio}" \
    "https://api.deepgram.com/v1/listen?${QS}" \
    -o "$json_out"

  if grep -q '"err_code"' "$json_out" 2>/dev/null; then
    echo "  ERROR de Deepgram en $base:"
    cat "$json_out"
    return 1
  fi
  echo "  OK: $json_out"
}

if [ "$#" -gt 0 ]; then
  for f in "$@"; do
    transcribe_one "$AUDIOS_DIR/$f"
  done
else
  shopt -s nullglob nocaseglob
  files=("$AUDIOS_DIR"/*.mp3 "$AUDIOS_DIR"/*.m4a "$AUDIOS_DIR"/*.wav)
  shopt -u nullglob nocaseglob
  if [ ${#files[@]} -eq 0 ]; then
    echo "No se encontraron .mp3/.m4a/.wav en $AUDIOS_DIR" >&2
    exit 1
  fi
  for f in "${files[@]}"; do
    transcribe_one "$f"
  done
fi

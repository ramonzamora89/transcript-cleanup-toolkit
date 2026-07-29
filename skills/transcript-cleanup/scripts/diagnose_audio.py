#!/usr/bin/env python3
"""
diagnose_audio.py — Chequeo rápido de calidad de una transcripción de Deepgram, antes de
invertir tiempo en limpieza fina.

Calcula palabras/minuto y reporta huecos de silencio largos (sin habla detectada). Una
conversación normal ronda 100-150 palabras/min. Si la densidad es mucho más baja y hay huecos
largos, es señal de que Deepgram no está detectando habla real por un problema de audio
(volumen bajo, típicamente) — no de que "no se habló mucho". Ver SKILL.md § Paso 0.5 para el
árbol de decisión completo (normalizar volumen, probar Whisper si el problema es eco/reverb).

Uso:
    python diagnose_audio.py <id>_deepgram.json [--gap-threshold 30] [--wpm-threshold 80]
"""
import json, sys, argparse

def fmt(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = int(s % 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deepgram_json")
    ap.add_argument("--gap-threshold", type=float, default=30.0,
                     help="segundos mínimos para reportar un hueco de silencio (default: 30)")
    ap.add_argument("--wpm-threshold", type=float, default=80.0,
                     help="palabras/minuto por debajo de las cuales se marca como sospechoso (default: 80)")
    args = ap.parse_args()

    d = json.load(open(args.deepgram_json, encoding="utf-8"))
    if isinstance(d, dict) and ("err_code" in d or "err_msg" in d):
        print("ERROR de Deepgram en el JSON:", d.get("err_msg") or d)
        sys.exit(2)

    dur = d["metadata"]["duration"]
    words = d["results"]["channels"][0]["alternatives"][0]["words"]
    wpm = len(words) / (dur / 60) if dur else 0

    print(f"Duración: {fmt(dur)} ({dur/60:.1f} min)")
    print(f"Palabras totales: {len(words)}")
    print(f"Palabras/minuto: {wpm:.1f}  (referencia: conversación normal ~100-150/min)")

    gaps = []
    prev_end = 0.0
    for w in words:
        if w["start"] - prev_end > args.gap_threshold:
            gaps.append((prev_end, w["start"]))
        prev_end = w["end"]
    if dur - prev_end > args.gap_threshold:
        gaps.append((prev_end, dur))

    total_gap = sum(b - a for a, b in gaps)
    pct_gap = (total_gap / dur * 100) if dur else 0

    print(f"\nHuecos sin habla detectada (> {args.gap_threshold:.0f}s): {len(gaps)}")
    print(f"Tiempo total en huecos: {total_gap:.0f}s ({pct_gap:.0f}% de la duración)")
    for a, b in gaps[:30]:
        print(f"  {fmt(a)} -> {fmt(b)}  ({b-a:.0f}s)")
    if len(gaps) > 30:
        print(f"  ... y {len(gaps) - 30} más")

    print()
    if wpm < args.wpm_threshold and pct_gap > 30:
        print("⚠️  SOSPECHOSO: densidad de palabras baja y huecos de silencio extensos.")
        print("    Probable problema de volumen, no falta de contenido. Antes de limpiar:")
        print("    1) ffmpeg -i audio.ext -af volumedetect -f null -   (revisar mean_volume)")
        print("    2) Si mean_volume < -25dB aprox., normalizar un fragmento de 60-90s de un")
        print("       hueco con loudnorm y volver a mandarlo a Deepgram para confirmar.")
        print("    3) Si funciona, normalizar el archivo completo y retranscribir (respaldar")
        print("       el JSON original antes de sobrescribir).")
        print("    Si tras normalizar los huecos persisten con volumen similar al resto del")
        print("    audio, probablemente sean silencios reales — no seguir insistiendo.")
    elif wpm < args.wpm_threshold:
        print("Densidad de palabras baja pero sin huecos largos concentrados — revisar si el")
        print("habla está dispersa en fragmentos muy cortos (posible eco/diarización difícil;")
        print("ver SKILL.md § Paso 0.5, cruce con whisper-large) o si el audio es genuinamente")
        print("poco denso (pausas frecuentes, silencios entre turnos).")
    else:
        print("Densidad de palabras dentro de lo esperable. No parece haber contenido perdido")
        print("por problema de audio.")

if __name__ == "__main__":
    main()

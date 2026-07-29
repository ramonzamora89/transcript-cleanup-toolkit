#!/usr/bin/env python3
"""
build_turns.py — Construye los turnos de la transcripción DIRECTO del JSON de Deepgram,
agrupando por `utterances` (ya viene agrupado por Deepgram con utt_split).

Uso:
    python build_turns.py <id>_deepgram.json [salida.json]

Qué hace:
  - Verifica que el JSON no sea un error de Deepgram.
  - Fusiona utterances consecutivas del mismo speaker en un turno.
  - Toma la hora real de inicio de cada turno (HH:MM:SS).
  - Reporta duración, idioma detectado, número de turnos y conteo por hablante.
  - Escribe salida.json con { duracion, duracion_seg, idioma_detectado, hablantes, turnos }.

NO alinear texto limpio contra el JSON. Construir SIEMPRE desde aquí (o desde
build_turns_words.py) y limpiar turno por turno sobre esa base — eso preserva timestamps y
atribución de hablante.

Ver también build_turns_words.py: cuando `utterances` funde intervenciones cortas de un
hablante distinto dentro del turno largo de otro (común con un solo micrófono o un hablante
dominante), reconstruir por palabra da una segmentación más fiel. Comparar el número de turnos
de ambos métodos antes de decidir cuál usar como base de la limpieza fina.
"""
import json, sys
from collections import Counter

def fmt(st):
    h = int(st // 3600); m = int((st % 3600) // 60); s = int(st % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def main():
    if len(sys.argv) < 2:
        print("Uso: python build_turns.py <id>_deepgram.json [salida.json]"); sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "merged.json"
    d = json.load(open(src, encoding="utf-8"))

    if isinstance(d, dict) and ("err_code" in d or "err_msg" in d):
        print("ERROR de Deepgram en el JSON:", d.get("err_msg") or d)
        sys.exit(2)

    dur = d["metadata"]["duration"]
    utts = d["results"]["utterances"]
    channel0 = d["results"].get("channels", [{}])[0]
    idioma = channel0.get("detected_language") or d["results"].get("detected_language")

    merged = []
    for u in utts:
        spk = u.get("speaker")
        if merged and merged[-1]["spk"] == spk:
            merged[-1]["text"] += " " + u["transcript"]
            merged[-1]["end"] = u["end"]
        else:
            merged.append({"spk": spk, "start": u["start"], "end": u["end"], "text": u["transcript"]})

    turnos = [{"i": i, "spk": m["spk"], "ts": fmt(m["start"]), "text": m["text"]}
              for i, m in enumerate(merged)]

    result = {
        "duracion": fmt(dur),
        "duracion_seg": dur,
        "idioma_detectado": idioma,
        "hablantes": dict(Counter(m["spk"] for m in merged)),
        "turnos": turnos,
    }
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Duración: {fmt(dur)} ({dur/60:.1f} min)")
    print(f"Idioma detectado: {idioma}")
    print(f"Utterances: {len(utts)}  |  Turnos fusionados: {len(merged)}")
    print(f"Hablantes (turnos): {result['hablantes']}")
    print(f"\nEscrito: {out} ({len(turnos)} turnos)")
    print("Primeros turnos (para identificar hablantes):")
    for t in turnos[:4]:
        print(f"  [{t['i']}] {t['ts']} spk{t['spk']}: {t['text'][:90]}")

if __name__ == "__main__":
    main()

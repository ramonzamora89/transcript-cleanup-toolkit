#!/usr/bin/env python3
"""
build_turns_words.py — Construye turnos DIRECTO de las etiquetas de hablante por PALABRA
(results.channels[0].alternatives[0].words), no de `utterances`.

En grabaciones con un solo micrófono, varios hablantes, o un hablante que domina la
conversación, el campo `utterances` de Deepgram (ya agrupado con utt_split) funde
intervenciones cortas de un hablante distinto (interjecciones, confirmaciones breves,
preguntas cortas) dentro del turno largo del otro hablante. Agrupar palabras consecutivas del
mismo `speaker` en turnos da una segmentación más fiel en ese tipo de audio — a veces incluso
recupera frases completas que la versión por utterance pierde del todo.

Comparar siempre el número de turnos resultante contra build_turns.py antes de decidir cuál usar
como base de `turns_ts.json`. Si el número es muy similar, no hace falta usar esta versión.

Uso:
    python build_turns_words.py <id>_deepgram.json [salida.json]
"""
import json, sys
from collections import Counter

def fmt(st):
    h = int(st // 3600); m = int((st % 3600) // 60); s = int(st % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def main():
    if len(sys.argv) < 2:
        print("Uso: python build_turns_words.py <id>_deepgram.json [salida.json]"); sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "merged_words.json"
    d = json.load(open(src, encoding="utf-8"))

    if isinstance(d, dict) and ("err_code" in d or "err_msg" in d):
        print("ERROR de Deepgram en el JSON:", d.get("err_msg") or d)
        sys.exit(2)

    dur = d["metadata"]["duration"]
    words = d["results"]["channels"][0]["alternatives"][0]["words"]

    turns = []
    for w in words:
        spk = w["speaker"]
        tok = w["punctuated_word"]
        if turns and turns[-1]["spk"] == spk:
            turns[-1]["text"] += " " + tok
            turns[-1]["end"] = w["end"]
        else:
            turns.append({"spk": spk, "start": w["start"], "end": w["end"], "text": tok})

    print(f"Duración: {fmt(dur)} ({dur/60:.1f} min)")
    print(f"Palabras: {len(words)}  |  Turnos (por palabra): {len(turns)}")
    print(f"Hablantes (turnos): {dict(Counter(t['spk'] for t in turns))}")

    result = [{"i": i, "spk": t["spk"], "ts": fmt(t["start"]), "text": t["text"]}
              for i, t in enumerate(turns)]
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nEscrito: {out}  ({len(result)} turnos)")
    print("Primeros turnos (para identificar hablantes):")
    for t in result[:4]:
        print(f"  [{t['i']}] {t['ts']} spk{t['spk']}: {t['text'][:90]}")

if __name__ == "__main__":
    main()

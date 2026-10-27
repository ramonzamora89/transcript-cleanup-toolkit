#!/usr/bin/env python3
"""
find_dudosos.py — Localiza en el tiempo cada tramo `[dudoso...]` / `[inaudible]` de
turns_ts.json, para poder cortar un clip y revisarlo escuchando (SKILL.md § Paso 2.5).

turns_ts.json ya está limpio, así que no hay correspondencia exacta carácter→palabra con el
JSON de Deepgram. La estimación es: ventana del turno (su `ts` hasta el `ts` del siguiente),
posición relativa de la marca dentro del texto del turno → posición relativa entre las palabras
de esa ventana, y ajuste al grupo de palabras de confianza baja más cercano. Es un punto de
partida: revisar `start`/`end` en dudosos.json antes de cortar los clips si algo no cuadra
(el texto ASR crudo de cada tramo queda en `asr` para comprobarlo).

Escribe <dir>/dudosos.json con una entrada por marca:
  {id, turn_i, label, ts, marcador, hipotesis, start, end, asr, contexto, opciones: []}
`opciones` queda vacío: lo completa Claude con las hipótesis razonadas (ver SKILL.md).

Uso:
    python find_dudosos.py <dir> <id>_deepgram.json [--conf 0.6] [--max-span 10]
"""
import json, os, re, sys, argparse

MARK = re.compile(r"\[(?:dudoso(?:\s*:\s*([^\]]*))?|inaudible)\]", re.IGNORECASE)

def fmt(st):
    h = int(st // 3600); m = int((st % 3600) // 60); s = int(st % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def parse_ts(ts):
    if ts is None:
        return None
    parts = [float(p) for p in str(ts).split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]

def clusters(idx):
    """Agrupa índices consecutivos (tolerando 1 palabra intermedia)."""
    out = []
    for i in idx:
        if out and i - out[-1][-1] <= 2:
            out[-1].append(i)
        else:
            out.append([i])
    return out

def locate(words, text, pos, conf, max_span):
    """Devuelve (i0, i1) índices de palabras para la marca en la posición `pos` del texto."""
    n = len(words)
    rel = pos / max(len(text), 1)
    center = min(int(rel * n), n - 1)
    low = [i for i, w in enumerate(words) if w.get("confidence", 1.0) < conf]
    if low:
        best = min(clusters(low), key=lambda c: min(abs(i - center) for i in c))
        # Solo aceptar el grupo si está razonablemente cerca de la posición estimada.
        if min(abs(i - center) for i in best) <= max(3, n // 4):
            i0, i1 = best[0], best[-1]
            while words[i1]["end"] - words[i0]["start"] > max_span and i1 > i0:
                if abs(i1 - center) >= abs(i0 - center):
                    i1 -= 1
                else:
                    i0 += 1
            return i0, i1
    i0 = i1 = center
    while i0 > 0 and words[center]["start"] - words[i0 - 1]["start"] < max_span / 2:
        i0 -= 1
    while i1 < n - 1 and words[i1 + 1]["end"] - words[center]["end"] < max_span / 2:
        i1 += 1
    return i0, i1

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # acentos legibles en la consola de Windows
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("deepgram_json")
    ap.add_argument("--conf", type=float, default=0.6,
                    help="confianza por debajo de la cual una palabra cuenta como dudosa (default: 0.6)")
    ap.add_argument("--max-span", type=float, default=10.0,
                    help="duración máxima en segundos de un tramo (default: 10)")
    args = ap.parse_args()

    d = json.load(open(args.deepgram_json, encoding="utf-8"))
    if isinstance(d, dict) and ("err_code" in d or "err_msg" in d):
        print("ERROR de Deepgram en el JSON:", d.get("err_msg") or d)
        sys.exit(2)
    words = d["results"]["channels"][0]["alternatives"][0]["words"]
    dur = d["metadata"]["duration"]

    turns = json.load(open(os.path.join(args.dir, "turns_ts.json"), encoding="utf-8"))
    timed = [(k, t) for k, t in enumerate(turns) if not t.get("note") and t.get("ts")]

    out = []
    for n, (k, t) in enumerate(timed):
        text = t.get("text", "")
        marks = list(MARK.finditer(text))
        if not marks:
            continue
        t0 = parse_ts(t["ts"])
        t1 = parse_ts(timed[n + 1][1]["ts"]) + 1 if n + 1 < len(timed) else dur
        win = [w for w in words if w["start"] >= t0 - 0.5 and w["start"] < t1]
        for m in marks:
            entry = {
                "id": f"d{len(out) + 1:02d}",
                "turn_i": t.get("i", k),
                "label": t.get("label"),
                "ts": t["ts"],
                "marcador": m.group(0),
                "hipotesis": (m.group(1) or "").strip() or None,
                "contexto": {"antes": text[max(0, m.start() - 160):m.start()],
                             "despues": text[m.end():m.end() + 160]},
                "opciones": [],
            }
            if win:
                i0, i1 = locate(win, text, m.start(), args.conf, args.max_span)
                entry["start"] = round(win[i0]["start"], 2)
                entry["end"] = round(win[i1]["end"], 2)
                entry["asr"] = " ".join(
                    f"{w.get('punctuated_word', w['word'])}({w.get('confidence', 1.0):.2f})"
                    for w in win[i0:i1 + 1])
            else:
                # Sin palabras detectadas en la ventana (típico de [inaudible]): usar el inicio del turno.
                entry["start"] = round(t0, 2)
                entry["end"] = round(min(t0 + args.max_span / 2, t1, dur), 2)
                entry["asr"] = ""
            out.append(entry)

    dst = os.path.join(args.dir, "dudosos.json")
    if os.path.exists(dst):
        prev = {e["marcador"] + str(e["turn_i"]): e for e in json.load(open(dst, encoding="utf-8"))}
        for e in out:
            old = prev.get(e["marcador"] + str(e["turn_i"]))
            if old and old.get("opciones"):
                e["opciones"] = old["opciones"]  # no perder opciones ya redactadas
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Tramos dudosos encontrados: {len(out)}")
    for e in out:
        print(f"  {e['id']}  turno {e['turn_i']}  {fmt(e['start'])}-{fmt(e['end'])}  "
              f"{e['marcador'][:50]}  ASR: {e['asr'][:70]}")
    print(f"\nEscrito: {dst}")
    print("Siguiente: completar `opciones` en cada entrada y cortar los clips con make_clips.py.")

if __name__ == "__main__":
    main()

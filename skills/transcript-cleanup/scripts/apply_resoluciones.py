#!/usr/bin/env python3
"""
apply_resoluciones.py — Aplica las elecciones de la revisión de dudosos (resoluciones.json) a
turns_ts.json y deja rastro en cfg.json → pendientes (SKILL.md § Paso 2.5).

Una elección del usuario es confirmación humana (principio 6): el texto elegido reemplaza la
marca sin `[dudoso]`. `inaudible` deja `[inaudible]`; `mantener` no toca nada y el tramo sigue
como pendiente.

Antes de escribir guarda turns_ts.before_review.json (solo la primera vez, para no pisar el
original con una corrida intermedia). Se puede volver a correr sin duplicar nada. Si una marca
ya no está en su turno (se editó a mano después de find_dudosos.py), avisa, no la toca y la deja
como pendiente.

Formato de resoluciones.json (igual desde la página o desde la CLI):
    { "d01": {"eleccion": "opcion"|"otro"|"inaudible"|"mantener", "texto": "...",
              "via": "pagina"|"cli", "fecha": "..."} }

Uso:
    python apply_resoluciones.py <dir>
"""
import json, os, shutil, sys

def fmt(st):
    h = int(st // 3600); m = int((st % 3600) // 60); s = int(st % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # acentos legibles en la consola de Windows
    if len(sys.argv) < 2:
        print("Uso: python apply_resoluciones.py <dir>"); sys.exit(1)
    d = sys.argv[1]
    p_turns, p_cfg = os.path.join(d, "turns_ts.json"), os.path.join(d, "cfg.json")
    turns = json.load(open(p_turns, encoding="utf-8"))
    items = json.load(open(os.path.join(d, "dudosos.json"), encoding="utf-8"))
    res = json.load(open(os.path.join(d, "resoluciones.json"), encoding="utf-8"))
    cfg = json.load(open(p_cfg, encoding="utf-8")) if os.path.exists(p_cfg) else {}

    by_i = {t.get("i", k): t for k, t in enumerate(turns) if not t.get("note")}
    applied, kept, missing, pend = [], [], [], []
    for e in items:
        r = res.get(e["id"])
        when = fmt(e["start"])
        if not r or r["eleccion"] == "mantener":
            kept.append(e["id"])
            pend.append(f"[{when}] {e['marcador']} — sin confirmar en la revisión de clips ({e['id']}).")
            continue
        t = by_i.get(e["turn_i"])
        new = "[inaudible]" if r["eleccion"] == "inaudible" else r["texto"].strip()
        if t and e["marcador"] in t["text"]:
            t["text"] = t["text"].replace(e["marcador"], new, 1)
        elif not (t and new in t["text"]):  # si `new` ya está, es una corrida anterior: no tocar
            missing.append(e["id"])
            pend.append(f"[{when}] {e['marcador']} — elegido «{new}» pero la marca ya no estaba en el turno; revisar a mano ({e['id']}).")
            continue
        applied.append(e["id"])
        if r["eleccion"] == "inaudible":
            pend.append(f"[{when}] Confirmado como [inaudible] en revisión humana ({e['id']}).")
        else:
            pend.append(f"[{when}] Confirmado en revisión humana: «{new}» (antes {e['marcador']}; {e['id']}).")

    if missing:
        print("AVISO: estas marcas ya no están en su turno y no se tocaron:", ", ".join(missing))
        print("       Volver a correr find_dudosos.py si se editó turns_ts.json después.")

    backup = os.path.join(d, "turns_ts.before_review.json")
    if not os.path.exists(backup):
        shutil.copyfile(p_turns, backup)
    json.dump(turns, open(p_turns, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if cfg:
        # Quitar las líneas que ya dejó una corrida anterior de este script y agregar las nuevas.
        ids = {e["id"] for e in items}
        old = [p for p in cfg.get("pendientes", [])
               if not any(f"({i})" in p or f"; {i})" in p for i in ids)]
        cfg["pendientes"] = old + pend
        json.dump(cfg, open(p_cfg, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"Aplicadas: {len(applied)}  |  Sin confirmar: {len(kept)}  |  No encontradas: {len(missing)}")
    print(f"Escrito: {p_turns}  (respaldo: {backup})")
    if cfg:
        print(f"Pendientes actualizados en {p_cfg}")
    print("Siguiente: node scripts/build_transcript.js", d)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_clips.py — Corta un clip por cada tramo de dudosos.json, para escucharlo (o verlo) durante
la revisión (SKILL.md § Paso 2.5).

Si la fuente tiene pista de video, los clips son .mp4 (H.264 + AAC) — útil para ver quién habla
o leer labios; si no, .mp3. El corte se re-codifica para que empiece justo donde debe (un corte
con copia de stream salta al keyframe más cercano y puede comerse el tramo).

Escribe <dir>/clips_dudosos/<id>_<HHMMSS>.<ext>, un índice clips_dudosos/index.md (para abrir
desde la terminal) y registra `clip` en cada entrada de dudosos.json.

Uso:
    python make_clips.py <dir> [<audio_o_video>] [--pre 1.5] [--post 1.0] [--audio-only]
Si se omite el archivo, usa `media` de <dir>/cfg.json (ruta relativa a <dir> o absoluta).
"""
import json, os, subprocess, sys, argparse, shutil

def fmt(st):
    h = int(st // 3600); m = int((st % 3600) // 60); s = int(st % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def has_video(media):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
                        "-show_entries", "stream=codec_type,disposition=attached_pic",
                        "-of", "json", media], capture_output=True, text=True)
    if r.returncode != 0:
        print("ERROR: ffprobe no pudo leer", media, "\n", r.stderr)
        sys.exit(2)
    streams = json.loads(r.stdout or "{}").get("streams", [])
    # La carátula embebida de un mp3/m4a cuenta como "video" para ffprobe: ignorarla.
    return any(not s.get("disposition", {}).get("attached_pic") for s in streams)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # acentos legibles en la consola de Windows
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("media", nargs="?")
    ap.add_argument("--pre", type=float, default=1.5, help="segundos de contexto antes del tramo")
    ap.add_argument("--post", type=float, default=1.0, help="segundos de contexto después del tramo")
    ap.add_argument("--audio-only", action="store_true", help="clips de audio aunque la fuente sea video")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            print(f"ERROR: no se encontró {tool} en el PATH."); sys.exit(1)

    media = args.media
    if not media:
        cfg_path = os.path.join(args.dir, "cfg.json")
        cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}
        media = cfg.get("media")
        if not media:
            print("ERROR: pasar el audio/video como argumento o definir `media` en cfg.json."); sys.exit(1)
        if not os.path.isabs(media):
            media = os.path.join(args.dir, media)
    if not os.path.exists(media):
        print("ERROR: no existe", media); sys.exit(1)

    src = os.path.join(args.dir, "dudosos.json")
    items = json.load(open(src, encoding="utf-8"))
    video = has_video(media) and not args.audio_only
    ext = "mp4" if video else "mp3"
    outdir = os.path.join(args.dir, "clips_dudosos")
    os.makedirs(outdir, exist_ok=True)

    for e in items:
        a = max(0.0, e["start"] - args.pre)
        length = (e["end"] + args.post) - a
        name = f"{e['id']}_{fmt(e['start']).replace(':', '')}.{ext}"
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.2f}", "-i", media, "-t", f"{length:.2f}"]
        if video:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
        else:
            cmd += ["-vn", "-c:a", "libmp3lame", "-q:a", "4"]
        r = subprocess.run(cmd + [os.path.join(outdir, name)], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"ERROR cortando {e['id']}:\n{r.stderr}"); sys.exit(2)
        e["clip"] = name
        e["clip_inicio"] = round(a, 2)  # para mostrar en qué segundo del clip empieza el tramo
        print(f"  {name}  ({fmt(a)} + {length:.1f}s)")

    json.dump(items, open(src, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    lines = ["# Tramos dudosos", "", f"Fuente: `{os.path.basename(media)}` · {len(items)} clips", ""]
    for e in items:
        lines += [f"## {e['id']} — [{fmt(e['start'])}] {e.get('label') or ''}".rstrip(), "",
                  f"- Clip: `{e['clip']}` (el tramo empieza ~{e['start'] - e['clip_inicio']:.1f}s dentro del clip)",
                  f"- Marca: `{e['marcador']}`",
                  f"- ASR crudo: {e.get('asr') or '(sin palabras detectadas)'}",
                  f"- Contexto: …{e['contexto']['antes'][-100:]} **{e['marcador']}** {e['contexto']['despues'][:100]}…"]
        for k, o in enumerate(e.get("opciones") or []):
            lines.append(f"  {chr(97 + k)}) {o}")
        lines.append("")
    open(os.path.join(outdir, "index.md"), "w", encoding="utf-8").write("\n".join(lines))

    print(f"\n{len(items)} clips ({ext}) en {outdir}")
    print(f"Índice: {os.path.join(outdir, 'index.md')}")

if __name__ == "__main__":
    main()

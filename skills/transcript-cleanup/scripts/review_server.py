#!/usr/bin/env python3
"""
review_server.py — Página local para revisar los tramos dudosos escuchando cada clip y eligiendo
una opción (SKILL.md § Paso 2.5, modo app Desktop). Solo stdlib; escucha en 127.0.0.1, así que
el audio no sale de la máquina.

Sirve assets/review.html, los clips de <dir>/clips_dudosos/ y una API mínima:
  GET  /api/dudosos     -> {id, items: dudosos.json, resoluciones: resoluciones.json}
  POST /api/resolucion  -> {id, eleccion: opcion|otro|inaudible|mantener, texto} ; guarda al instante
  POST /api/fin         -> marca la revisión como terminada y apaga el servidor

Cada elección se escribe en <dir>/resoluciones.json en cuanto se hace (tmp + rename), así que
cerrar la página a medias no pierde nada. Después: apply_resoluciones.py <dir>.

Uso:
    python review_server.py <dir> [--port 8765]
"""
import json, os, re, sys, argparse, threading, datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "assets", "review.html")
TYPES = {".mp3": "audio/mpeg", ".mp4": "video/mp4", ".m4a": "audio/mp4", ".wav": "audio/wav"}
LOCK = threading.Lock()

def load(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default

def save(path, data):
    tmp = path + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, path)

def make_handler(d):
    res_path = os.path.join(d, "resoluciones.json")
    cfg = load(os.path.join(d, "cfg.json"), {})

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            p = self.path.split("?")[0]
            if p in ("/", "/index.html"):
                return self.send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
            if p == "/api/dudosos":
                return self.send(200, {"id": cfg.get("id") or os.path.basename(os.path.abspath(d)),
                                       "items": load(os.path.join(d, "dudosos.json"), []),
                                       "resoluciones": load(res_path, {})})
            if p.startswith("/clips/"):
                return self.clip(os.path.basename(p[len("/clips/"):]))
            self.send(404, {"error": "no encontrado"})

        def clip(self, name):
            f = os.path.join(d, "clips_dudosos", name)
            if not name or not os.path.isfile(f):
                return self.send(404, {"error": "clip no encontrado"})
            size = os.path.getsize(f)
            ctype = TYPES.get(os.path.splitext(name)[1].lower(), "application/octet-stream")
            m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            with open(f, "rb") as fh:
                if not m or (not m.group(1) and not m.group(2)):
                    return self.send(200, fh.read(), ctype, {"Accept-Ranges": "bytes"})
                if m.group(1):
                    a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else size - 1
                else:  # bytes=-N: los últimos N bytes
                    a = max(0, size - int(m.group(2))); b = size - 1
                b = min(b, size - 1)
                if a > b:
                    return self.send(416, b"", ctype, {"Content-Range": f"bytes */{size}"})
                fh.seek(a)
                self.send(206, fh.read(b - a + 1), ctype,
                          {"Accept-Ranges": "bytes", "Content-Range": f"bytes {a}-{b}/{size}"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self.send(400, {"error": "JSON inválido"})
            now = datetime.datetime.now().isoformat(timespec="seconds")
            if self.path == "/api/resolucion":
                if body.get("eleccion") not in ("opcion", "otro", "inaudible", "mantener") or not body.get("id"):
                    return self.send(400, {"error": "falta id o eleccion válida"})
                if body["eleccion"] in ("opcion", "otro") and not (body.get("texto") or "").strip():
                    return self.send(400, {"error": "falta el texto"})
                with LOCK:
                    res = load(res_path, {})
                    res[body["id"]] = {"eleccion": body["eleccion"], "texto": (body.get("texto") or "").strip(),
                                       "via": "pagina", "fecha": now}
                    save(res_path, res)
                print(f"  {body['id']}: {body['eleccion']} {body.get('texto') or ''}".rstrip(), flush=True)
                return self.send(200, {"ok": True, "total": len(res)})
            if self.path == "/api/fin":
                self.send(200, {"ok": True})
                print(f"Revisión terminada. Resoluciones en {res_path}", flush=True)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            self.send(404, {"error": "no encontrado"})

    return H

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # acentos legibles en la consola de Windows
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if not os.path.exists(os.path.join(args.dir, "dudosos.json")):
        print("ERROR: no hay dudosos.json en", args.dir, "— correr find_dudosos.py y make_clips.py antes.")
        sys.exit(1)
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.dir))
    except OSError:
        print(f"ERROR: el puerto {args.port} está ocupado. Probar con --port {args.port + 1}.")
        sys.exit(1)
    print(f"Revisión de dudosos: http://127.0.0.1:{args.port}/", flush=True)
    print("Ctrl+C o el botón «Terminé» de la página para cerrar.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

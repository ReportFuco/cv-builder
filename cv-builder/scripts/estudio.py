"""Estudio de diseño: vista previa en vivo de una versión de CV para elegir plantilla, paleta, fuentes y escala.

    python cv-builder/scripts/estudio.py perfiles/<persona>/cvs/<version>.yaml [--puerto 8765] [--no-abrir]

Servidor local (solo librería estándar + render.py). Abre la página en el navegador.
- Cada cambio genera el HTML con `render.py --solo-html` sobre una copia temporal en perfiles/<persona>/.estudio/
  (no toca el YAML real ni cvs/salida/) y, al quedar quieto, corre el render completo con `--json` para el chequeo.
- «Guardar» escribe SOLO `plantilla`, `tema`, `foto` y `breve` en el YAML real, editando esas líneas (los
  comentarios se conservan), corre el render completo y deja rastro para los agentes:
  cvs/historial.jsonl (una línea por guardado) y la imagen en cvs/salida/historial/<version>-<fecha>.png.
Se corre desde la raíz del proyecto. Ctrl+C para salir (borra .estudio/).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parent.parent
RENDER = SKILL / "scripts" / "render.py"
PAGE = SKILL / "estudio" / "index.html"
KEYS = ("plantilla", "tema", "foto", "breve")          # lo único que el estudio puede cambiar


class Estudio:
    def __init__(self, vpath: Path):
        self.vpath = vpath
        self.person = vpath.parent.parent
        self.root = self.person.parent.parent               # raíz del proyecto (donde está perfiles/)
        self.tmp_dir = self.person / ".estudio"              # misma profundidad que cvs/: render.py halla perfil.yaml
        self.tmp = self.tmp_dir / vpath.name
        self.lock = threading.Lock()                         # un render a la vez
        self.listado = json.loads(self.run("--listar"))
        temas = yaml.safe_load((SKILL / "templates" / "temas.yaml").read_text(encoding="utf-8"))   # solo lectura
        self.colores = {k: [v[c] for c in ("primary", "secondary", "soft", "panel")] for k, v in temas["paletas"].items()}

    # ---------- render.py ----------

    def run(self, *args: str) -> str:
        r = subprocess.run([sys.executable, str(RENDER), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=self.root)
        if r.returncode != 0 and not r.stdout.strip().startswith("{"):
            raise RuntimeError((r.stdout + r.stderr).strip() or f"render.py salió con código {r.returncode}")
        return r.stdout

    def run_json(self, *args: str) -> dict:
        out = self.run(*args, "--json")
        start = out.find("{")                                 # por si render.py imprime algo antes del JSON
        return json.loads(out[start:])

    # ---------- estado ----------

    def version(self) -> dict:
        return yaml.safe_load(self.vpath.read_text(encoding="utf-8")) or {}

    def estado(self, v: dict | None = None) -> dict:
        """Lo que se ve en los controles: plantilla, tema completo (con el por_defecto), foto y breve."""
        v = v if v is not None else self.version()
        plantilla = v.get("plantilla", "ruta")
        tema = {"escala": 1.0, **self.listado["por_defecto"].get(plantilla, {}), **(v.get("tema") or {})}
        return {"plantilla": plantilla, "tema": tema,
                "foto": bool(v.get("foto", v.get("pais", "CL") != "CL")), "breve": bool(v.get("breve", False))}

    def claves(self, e: dict) -> dict:
        """Estado de la página -> claves para el YAML. `tema` solo guarda lo que difiere del por_defecto."""
        defecto = self.listado["por_defecto"].get(e["plantilla"], {})
        tema = {k: e["tema"][k] for k in ("paleta", "fuentes") if e["tema"].get(k) and e["tema"][k] != defecto.get(k)}
        escala = round(float(e["tema"].get("escala", 1)), 2)
        if escala != 1:
            tema["escala"] = escala
        return {"plantilla": e["plantilla"], "tema": tema or None, "foto": bool(e["foto"]), "breve": bool(e["breve"])}

    def write_tmp(self, e: dict) -> None:
        v = {**self.version(), **self.claves(e)}
        if v.get("tema") is None:
            v.pop("tema", None)
        self.tmp_dir.mkdir(exist_ok=True)
        self.tmp.write_text(yaml.safe_dump(v, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # ---------- acciones ----------

    def preview(self, e: dict) -> dict:
        with self.lock:
            self.write_tmp(e)
            out = self.run_json(str(self.tmp), "--solo-html", "--sin-validar")
        return {"html": self.url_for(Path(out["html"]))}

    def chequeo(self, e: dict) -> dict:
        with self.lock:
            self.write_tmp(e)
            out = self.run_json(str(self.tmp))
        return {**out, "png": self.url_for(Path(out["png"]))}

    def guardar(self, e: dict) -> dict:
        with self.lock:
            antes = {k: self.version().get(k) for k in KEYS}
            nuevas = self.claves(e)
            with self.vpath.open(encoding="utf-8", newline="") as f:   # newline="": respeta LF/CRLF del archivo
                text = f.read()
            for k in KEYS:
                text = set_key(text, k, nuevas[k])
            with self.vpath.open("w", encoding="utf-8", newline="") as f:
                f.write(text)
            despues = {k: self.version().get(k) for k in KEYS}
            out = self.run_json(str(self.vpath))

            ahora = dt.datetime.now().replace(microsecond=0)
            hist_dir = self.vpath.parent / "salida" / "historial"
            hist_dir.mkdir(parents=True, exist_ok=True)
            png = hist_dir / f"{self.vpath.stem}-{ahora:%Y-%m-%dT%H-%M-%S}.png"
            shutil.copy2(out["png"], png)
            linea = {"fecha": ahora.isoformat(), "version": self.vpath.name, "quien": "estudio",
                     "antes": antes, "despues": despues, "png": png.relative_to(self.vpath.parent).as_posix()}
            with (self.vpath.parent / "historial.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(linea, ensure_ascii=False, default=str) + "\n")
        return {**out, "png": self.url_for(png), "historial": linea}

    # ---------- archivos ----------

    def url_for(self, path: Path) -> str:
        return "/archivo/" + urllib.parse.quote(path.resolve().as_posix()) + f"?t={dt.datetime.now().timestamp():.0f}"

    def allowed(self, path: Path) -> bool:
        path = path.resolve()
        return any(path.is_relative_to(base) for base in (self.root.resolve(), SKILL))

    def serve_file(self, path: Path) -> tuple[bytes, str]:
        data = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".html":                           # file:///... -> /archivo/... para que el iframe cargue
            html = data.decode("utf-8")                      # fuentes, foto y recursos desde este servidor
            html = re.sub(r"file:///([^\"')\s]+)", lambda m: "/archivo/" + m[1], html)
            data, ctype = html.encode("utf-8"), "text/html; charset=utf-8"
        return data, ctype


def set_key(text: str, key: str, value) -> str:
    """Escribe `key: value` en la raíz del YAML sin tocar el resto (comentarios incluidos).
    Reemplaza la línea (y su bloque indentado si lo tenía) conservando el comentario final; si no existe, la agrega
    debajo de `plantilla:` (o al final de la cabecera). value None = borrar la clave."""
    lines = text.splitlines(keepends=True)
    eol = "\r\n" if "\r\n" in text else "\n"
    if isinstance(value, dict):
        rendered = "{ " + ", ".join(f"{k}: {v}" for k, v in value.items()) + " }"
    elif isinstance(value, bool):
        rendered = "true" if value else "false"
    else:
        rendered = str(value)
    pat = re.compile(rf"^{re.escape(key)}:(?P<val>[^#\n]*)(?P<com>#.*)?$")
    for i, line in enumerate(lines):
        m = pat.match(line.rstrip("\r\n"))
        if not m:
            continue
        end = i + 1                                          # bloque indentado de la clave (tema en varias líneas)
        while end < len(lines) and lines[end].startswith((" ", "\t")) and lines[end].strip():
            end += 1
        if value is None:
            return "".join(lines[:i] + lines[end:])
        com = m["com"] or ""
        pad = " " * max(1, len(m["val"]) - len(rendered) - 1) if com else ""
        nl = line[len(line.rstrip("\r\n")):]
        return "".join(lines[:i] + [f"{key}: {rendered}{pad + com if com else ''}{nl}"] + lines[end:])
    if value is None:
        return text
    anchor = next((i for i, l in enumerate(lines) if l.startswith("plantilla:")), None)
    if anchor is None:
        anchor = next((i for i, l in enumerate(lines) if re.match(r"^\w+:", l)), len(lines) - 1)
    lines.insert(anchor + 1, f"{key}: {rendered}{eol}")
    return "".join(lines)


def handler_for(st: Estudio):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):                            # silencio: la consola es para errores
            pass

        def send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, obj, code: int = 200) -> None:
            self.send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path in ("/", "/index.html"):
                return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if path == "/api/estado":
                return self.send_json({"version": st.vpath.relative_to(st.root).as_posix(),
                                       "persona": st.person.name, "listado": st.listado, "colores": st.colores,
                                       "estado": st.estado()})
            if path.startswith("/archivo/"):
                f = Path(urllib.parse.unquote(path[len("/archivo/"):]))
                if st.allowed(f) and f.is_file():
                    return self.send(200, *st.serve_file(f))
                return self.send(404, b"no encontrado", "text/plain")
            self.send(404, b"no encontrado", "text/plain")

        def do_POST(self):
            acciones = {"/api/preview": st.preview, "/api/chequeo": st.chequeo, "/api/guardar": st.guardar}
            accion = acciones.get(urllib.parse.urlparse(self.path).path)
            if accion is None:
                return self.send(404, b"no encontrado", "text/plain")
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                self.send_json(accion(body))
            except Exception as exc:                          # el error va a la página, no se cae el servidor
                self.send_json({"error": str(exc)}, 500)
    return Handler


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version", type=Path)
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    a = ap.parse_args()

    vpath = a.version.resolve()
    if not vpath.is_file() or vpath.parent.name != "cvs":
        sys.exit(f"ERROR «{a.version}» no es una versión (perfiles/<persona>/cvs/<version>.yaml)")
    st = Estudio(vpath)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", a.puerto), handler_for(st))
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(st))   # puerto ocupado: uno libre
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Estudio de «{st.person.name}/{vpath.name}» en {url}  (Ctrl+C para salir)")
    if not a.no_abrir:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        shutil.rmtree(st.tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()

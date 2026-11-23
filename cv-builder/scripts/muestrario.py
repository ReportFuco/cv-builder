"""Genera el muestrario de diseños de una persona: cada versión × plantilla × paleta × fuentes, en PDF y WebP.

    python muestrario.py perfiles/<persona> [--plantillas ola,lateral,ruta] [--versiones data,desarrollo]

Salida en perfiles/<persona>/muestrario/:
  paquete/<version>.webp, <version>-paquete.pdf, manifest.json   lo que usa la página «Elige tu CV» (cv-builder/elige/)
  (pdf/ e img/ sueltos se borran al empaquetar; --conservar-sueltos los deja)

Usa las mismas funciones que render.py (contexto, temas, ajuste a la página y chequeo) con un solo navegador.
No toca los YAML de la persona: el tema se aplica en memoria. La página «Elige tu CV» lee el manifest.
"""
from __future__ import annotations

import argparse
import shutil
import datetime as dt
import importlib.util
import io
import json
import sys
import tempfile
import time
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("render", HERE / "render.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

# Para qué sirve cada plantilla (lo muestra la página, para que la elección sea didáctica).
PLANTILLAS = {
    "ola": {"nombre": "Ola", "para": "Visual y con foto: encabezado de color con una ola. Bueno para LinkedIn, ferias y postulaciones directas.",
            "ats": "Dos columnas que el ATS lee en orden."},
    "lateral": {"nombre": "Lateral", "para": "Moderno: barra de color con foto y contacto, nombre grande al lado. Bueno para tecnología y startups.",
                "ats": "Dos columnas que el ATS lee en orden."},
    "ruta": {"nombre": "Ruta", "para": "Sobrio: una columna y la experiencia como ruta con paradas. Bueno para portales de empleo y empresas grandes.",
             "ats": "Una columna: lo más seguro para un ATS."},
    "clasica": {"nombre": "Clásica", "para": "Máximo ATS: una columna, sin color de fondo, al estilo de los CV técnicos en inglés.",
                "ats": "Una columna, sin adornos."},
}


SPRITE_COLS = 9


def empaquetar(out: Path, conservar: bool = False) -> None:
    """Junta el muestrario en pocos archivos para publicarlo en una página (artifact):
    paquete/<version>.webp  grilla con todas las vistas previas (SPRITE_COLS columnas)
    paquete/<version>-paquete.pdf  todos los PDF concatenados (extensión .pdf porque los artifacts no sirven .bin); manifest.json guarda [inicio, largo] de cada uno.
    """
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    pk = out / "paquete"
    pk.mkdir(exist_ok=True)
    for v in manifest["versiones"]:
        combos = sorted(v["combos"])
        tiles = [Image.open(out / "img" / v["id"] / f"{c}.webp") for c in combos]
        w, h = tiles[0].size
        rows = -(-len(tiles) // SPRITE_COLS)
        sheet = Image.new("RGB", (w * SPRITE_COLS, h * rows), "white")
        blob, pos = bytearray(), {}
        for k, (c, im) in enumerate(zip(combos, tiles)):
            sheet.paste(im, ((k % SPRITE_COLS) * w, (k // SPRITE_COLS) * h))
            data = (out / "pdf" / v["id"] / f"{c}.pdf").read_bytes()
            pos[c] = [len(blob), len(data)]
            blob += data
            v["combos"][c].update({"celda": k, "pdf": pos[c]})
        sheet.save(pk / f"{v['id']}.webp", "WEBP", quality=80, method=6)
        (pk / f"{v['id']}-paquete.pdf").write_bytes(bytes(blob))
        v["sprite"] = {"archivo": f"{v['id']}.webp", "cols": SPRITE_COLS, "filas": rows, "ancho": w, "alto": h}
        v["pdfs"] = f"{v['id']}-paquete.pdf"
    (pk / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    if not conservar:   # la página solo usa paquete/; los sueltos se regeneran con muestrario.py
        for d in ("pdf", "img"):
            shutil.rmtree(out / d, ignore_errors=True)
    sizes = sum(f.stat().st_size for f in pk.iterdir()) / 1e6
    print(f"Paquete: {pk} ({len(list(pk.iterdir()))} archivos, {sizes:.1f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("persona", type=Path)
    ap.add_argument("--plantillas", default="ola,lateral,ruta")
    ap.add_argument("--versiones", default="", help="por defecto, todas las de cvs/")
    ap.add_argument("--empaquetar", action="store_true", help="solo empaquetar lo ya generado (para publicar)")
    ap.add_argument("--conservar-sueltos", action="store_true", help="no borrar pdf/ e img/ después de empaquetar")
    args = ap.parse_args()

    person = args.persona.resolve()
    if args.empaquetar:
        empaquetar(person / "muestrario", args.conservar_sueltos)
        return
    profile = yaml.safe_load((person / "perfil.yaml").read_text(encoding="utf-8"))
    vfiles = sorted((person / "cvs").glob("*.yaml"))
    if args.versiones:
        vfiles = [person / "cvs" / f"{v}.yaml" for v in args.versiones.split(",")]
    themes = R.load_themes()
    plantillas = args.plantillas.split(",")
    out = person / "muestrario"
    manifest = {
        "persona": {"id": person.name, "nombre": profile["basics"]["name"]},
        "generado": dt.datetime.now().isoformat(timespec="minutes"),
        "plantillas": {p: PLANTILLAS.get(p, {"nombre": p.title(), "para": "", "ats": ""}) for p in plantillas},
        "paletas": {k: {"nombre": v["nombre"], "primary": v["primary"], "secondary": v["secondary"], "soft": v["soft"]}
                    for k, v in themes["paletas"].items()},
        "fuentes": {k: {"nombre": v["nombre"], "head": v["head"]["familia"],
                        "body": v["body"]["familia"], "archivo_head": v["head"]["archivos"][0]["archivo"],
                        "archivo_body": v["body"]["archivos"][0]["archivo"]}
                    for k, v in themes["fuentes"].items()},
        "versiones": [],
    }

    total, t0 = 0, time.time()
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=1)
        for vf in vfiles:
            base = yaml.safe_load(vf.read_text(encoding="utf-8"))
            vid = vf.stem
            entry = {"id": vid, "titulo": base.get("label", "").split("|")[0].strip(), "objetivo": base.get("objetivo"),
                     "actual": {"plantilla": base.get("plantilla", "ruta"), **(base.get("tema") or {})}, "combos": {}}
            for d in ("pdf", "img"):
                (out / d / vid).mkdir(parents=True, exist_ok=True)
            for pl in plantillas:
                for pa in themes["paletas"]:
                    for fu in themes["fuentes"]:
                        version = {**base, "plantilla": pl, "tema": {"paleta": pa, "fuentes": fu}}
                        ctx = R.build_context(profile, version, False, person)
                        tpl_dir = R.TEMPLATES / pl
                        env = Environment(loader=FileSystemLoader([tpl_dir, R.TEMPLATES]),
                                          autoescape=select_autoescape(["html", "j2"]))
                        env.filters["short"] = R.short_url
                        html = env.get_template("cv.html.j2").render(
                            css=R.build_css(tpl_dir, R.pick_theme(pl, version)), **ctx)
                        combo = f"{pl}-{pa}-{fu}"
                        hp = Path(tmp) / f"{vid}-{combo}.html"
                        hp.write_text(html, encoding="utf-8")
                        page.goto(hp.as_uri())
                        page.evaluate("document.fonts.ready")
                        fit = page.evaluate(R.FIT_JS, version.get("paginas_max", 1))
                        pdf = out / "pdf" / vid / f"{combo}.pdf"
                        page.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
                        shot = Image.open(io.BytesIO(page.screenshot(full_page=False))).convert("RGB")
                        shot.resize((600, round(shot.height * 600 / shot.width)), Image.LANCZOS).save(
                            out / "img" / vid / f"{combo}.webp", "WEBP", quality=82)
                        notes = R.check(pdf, ctx, version)
                        errors = [n[6:] for n in notes if n.startswith("ERROR")]
                        entry["combos"][combo] = {"ajuste": fit, "errores": errors}
                        total += 1
                        if errors:
                            print(f"ERROR {vid}/{combo}: {'; '.join(errors)}")
            manifest["versiones"].append(entry)
            print(f"{vid}: {len(entry['combos'])} combinaciones ({time.time() - t0:.0f} s)")
        browser.close()

    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = sum(1 for v in manifest["versiones"] for c in v["combos"].values() if c["errores"])
    empaquetar(out, args.conservar_sueltos)   # siempre deja el paquete listo para la página
    print(f"Listo: {total} combinaciones en {time.time() - t0:.0f} s, {bad} con errores. Manifest: {out / 'manifest.json'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

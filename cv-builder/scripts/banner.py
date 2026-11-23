"""Genera el banner de LinkedIn (1584 × 396) de una versión de CV, con su mismo tema (paleta y fuentes).

    python banner.py perfiles/<persona>/cvs/<version>.yaml [--estilo cifras|ruta|frase|formas|todos]
                     [--paleta <nombre>] [--fuentes <nombre>]

Salida en cvs/salida/banner/:
  <version>-<estilo>.png         para subir a LinkedIn (3168 × 792: el doble, se ve nítido en pantallas retina)
  <version>-<estilo>-zonas.png   la misma imagen marcando lo que tapa LinkedIn (foto de perfil y bordes)

El contenido sale de la versión: titular (`label`), herramientas, resumen, trayectoria (`work`) y, si existe, la clave
`banner` (`estilo`, `antetitulo`, `titulo`, `herramientas`, `frase`, `cifras`, `ruta`, `url`, `tema`). Las cifras no se inventan:
si no hay `banner.cifras`, el estilo «cifras» muestra la frase y el chequeo sugiere candidatas desde los logros.
Al final imprime el chequeo: texto bajo la foto o en los bordes, texto cortado y letra demasiado chica.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("render", HERE / "render.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)                     # temas y utilidades compartidas con el CV

BANNERS = HERE.parent / "banners"
ESTILOS = ("cifras", "ruta", "frase", "formas")
W, H = 1584, 396
PHOTO = (40 + 160, 160 + 160, 160)              # centro x, centro y, radio: foto de perfil en escritorio (aprox.)
EDGE = 80                                       # márgenes laterales que el celular puede recortar
MIN_PX = 22                                     # a ~50 % de escala en escritorio queda en ~11 px

CHECK_JS = """([cx, cy, r, edge, w, h, minPx]) => {
  const out = [];
  const els = document.querySelectorAll('.content h1, .content p, .content .val, .content .cap, .content .name, .content .year');
  for (const el of els) {
    if (!el.textContent.trim()) continue;
    const b = el.getBoundingClientRect();
    const label = el.textContent.trim().slice(0, 40);
    // rectángulo contra círculo: punto del rectángulo más cercano al centro de la foto
    const nx = Math.max(b.left, Math.min(cx, b.right)), ny = Math.max(b.top, Math.min(cy, b.bottom));
    if ((nx - cx) ** 2 + (ny - cy) ** 2 < r * r) out.push(['ERROR', `texto bajo la foto de perfil: «${label}»`]);
    if (b.left < edge || b.right > w - edge) out.push(['AVISO', `texto en el borde que el celular puede recortar: «${label}»`]);
    if (b.top < 0 || b.bottom > h || el.scrollWidth > el.clientWidth + 1) out.push(['ERROR', `texto cortado: «${label}»`]);
    const px = parseFloat(getComputedStyle(el).fontSize);
    if (px < minPx) out.push(['AVISO', `letra de ${px.toFixed(0)} px (mínimo ${minPx}): «${label}»`]);
  }
  return out;
}"""


def first_sentence(text: str | None) -> str:
    text = " ".join((text or "").split())
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return (m[1] if m else text).rstrip(".")


def trayectoria(profile: dict, version: dict) -> list[dict]:
    """Empresas de la versión, de la más antigua a la actual (una parada por empresa), máximo 4.
    Los cargos `compact` de la versión (secundarios) no cuentan."""
    jobs = {w["id"]: w for w in profile.get("work", [])}
    specs = [s if isinstance(s, dict) else {"id": s} for s in version.get("work") or jobs]
    ids = [s["id"] for s in specs if not s.get("compact")]
    por_empresa: dict[str, dict] = {}
    for w in sorted((jobs[i] for i in ids if i in jobs), key=lambda w: str(w.get("startDate") or "")):
        nombre = re.sub(r"\s*\(.*?\)", "", w["name"]).strip()
        anio = str(w.get("startDate") or "")[:4]
        prev = por_empresa.get(nombre)
        por_empresa[nombre] = {"nombre": nombre, "anio": prev["anio"] if prev else anio, "actual": not w.get("endDate")}
    return list(por_empresa.values())[-4:]


def candidatas(profile: dict) -> list[str]:
    """Métricas de los logros más fuertes, para sugerir `banner.cifras` (no se usan solas: hay que redactarlas)."""
    hls = [h for w in profile.get("work", []) + profile.get("projects", [])
           for h in (w.get("highlights") or []) if isinstance(h, dict) and h.get("metric")]
    hls.sort(key=lambda h: h.get("priority", 9))
    return [h["metric"] for h in hls[:5]]


def contexto(profile: dict, version: dict, estilo: str) -> dict:
    spec = version.get("banner") or {}
    label = version.get("label") or profile["basics"].get("label", "")
    rol, _, tools = label.partition("|")
    perfiles = profile["basics"].get("profiles") or []
    url_def = next((p["url"] for p in perfiles if p.get("network") == "GitHub"), None)
    actual = next((w for w in profile.get("work", []) if not w.get("endDate")), None)
    return {
        "estilo": estilo, "lang": version.get("idioma", "es"),
        "antetitulo": spec.get("antetitulo") or (actual or {}).get("name", ""),
        "titulo": spec.get("titulo") or rol.strip(),
        "herramientas": spec.get("herramientas") or [t.strip() for t in tools.split(",") if t.strip()],
        "frase": spec.get("frase") or first_sentence(version.get("summary")),
        "cifras": (spec.get("cifras") or [])[:3],
        "ruta": spec.get("ruta") or trayectoria(profile, version),
        "url": R.short_url(spec["url"] if "url" in spec else url_def or ""),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Banner de LinkedIn desde una versión de CV.")
    ap.add_argument("version", type=Path)
    ap.add_argument("--estilo", choices=(*ESTILOS, "todos"))
    ap.add_argument("--paleta")
    ap.add_argument("--fuentes")
    a = ap.parse_args()

    vpath = a.version.resolve()
    person = vpath.parent.parent
    profile = yaml.safe_load((person / "perfil.yaml").read_text(encoding="utf-8"))
    version = yaml.safe_load(vpath.read_text(encoding="utf-8"))
    spec = version.get("banner") or {}

    tema = {**(version.get("tema") or {}), **(spec.get("tema") or {}),
            **{k: v for k, v in (("paleta", a.paleta), ("fuentes", a.fuentes)) if v}}
    theme = R.pick_theme(version.get("plantilla", "ruta"), {"tema": tema})
    css = (BANNERS / "banner.css").read_text(encoding="utf-8") + R.theme_css(theme)
    env = Environment(loader=FileSystemLoader(BANNERS), autoescape=select_autoescape(["html", "j2"]))

    estilo = a.estilo or spec.get("estilo") or "todos"
    estilos = ESTILOS if estilo == "todos" else (estilo,)
    out = vpath.parent / "salida" / "banner"
    out.mkdir(parents=True, exist_ok=True)
    print(f"Banner de «{person.name}/{vpath.name}»: paleta «{theme['paleta']}», fuentes «{theme['fuentes']}»")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for e in estilos:
            ctx = contexto(profile, version, e)
            html_path = out / f"{vpath.stem}-{e}.html"
            html_path.write_text(env.get_template("banner.html.j2").render(css=css, **ctx), encoding="utf-8")
            page.goto(html_path.as_uri())
            page.evaluate("document.fonts.ready")
            png = out / f"{vpath.stem}-{e}.png"
            page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": W, "height": H})
            notes = page.evaluate(CHECK_JS, [*PHOTO, EDGE, W, H, MIN_PX])
            page.evaluate("document.body.classList.add('zonas')")
            page.screenshot(path=str(out / f"{vpath.stem}-{e}-zonas.png"), clip={"x": 0, "y": 0, "width": W, "height": H})

            print(f"\n{e}: {png}")
            if e == "frase" and len(ctx["frase"]) > 100:
                notes.append(["AVISO", f"frase de {len(ctx['frase'])} caracteres: en el celular se lee mejor con "
                                       "menos de 100 (escribe banner.frase)"])
            if e == "cifras" and not ctx["cifras"]:
                notes.append(["AVISO", "sin banner.cifras: se muestra la frase. Candidatas de los logros: "
                                       + " | ".join(candidatas(profile))])
            for lvl, txt in notes or [["OK", "texto fuera de la foto y de los bordes, sin cortes"]]:
                print(f"  {lvl:<5} {txt}")
        browser.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()

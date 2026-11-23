"""Genera un CV a partir de un perfil base y una versión.

    python render.py <perfiles/persona/cvs/version.yaml> [--borrador]

Salida en <cvs>/salida/: <version>.html, .pdf, .png y .json (JSON Resume puro).
Al final imprime el chequeo: páginas, orden de lectura del PDF (lo que ve un ATS) y avisos de contenido.
"""
from __future__ import annotations

import argparse
import base64
import shutil
import subprocess
import copy
import datetime as dt
import json
import re
import sys
from pathlib import Path

import pymupdf
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "templates"

# Etiquetas que cada objetivo prioriza (ver references/objetivos.md).
OBJECTIVE_TAGS = {
    "data": ["data", "automatizacion", "procesos"],
    "desarrollo": ["desarrollo", "automatizacion", "ia"],
    "automatizacion": ["automatizacion", "procesos", "ia"],
    "procesos": ["procesos", "gestion", "data"],
    "operaciones": ["logistica", "procesos", "gestion"],
    "liderazgo": ["liderazgo", "gestion"],
    "infraestructura": ["infraestructura", "seguridad", "desarrollo", "automatizacion"],
}

I18N = {
    "es": {
        "lang": "es", "work": "Experiencia", "projects": "Proyectos", "skills": "Habilidades",
        "education": "Educación", "certificates": "Certificaciones", "languages": "Idiomas", "profile": "Perfil", "contact": "Contacto",
        "present": "actualidad", "expected": "egreso",
        "months": "ene. feb. mar. abr. may. jun. jul. ago. sept. oct. nov. dic.".split(),
    },
    "en": {
        "lang": "en", "work": "Experience", "projects": "Projects", "skills": "Skills",
        "education": "Education", "certificates": "Certifications", "languages": "Languages", "profile": "Profile", "contact": "Contact",
        "present": "Present", "expected": "expected",
        "months": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(),
    },
}
DEFAULT_SECTIONS = ["work", "projects", "skills", "education", "certificates", "languages"]


# ---------- utilidades ----------

def ym(value) -> tuple[int, int] | None:
    """'2026-09' (o date) -> (2026, 9)."""
    if value in (None, ""):
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.year, value.month
    m = re.match(r"(\d{4})(?:-(\d{1,2}))?", str(value))
    return (int(m[1]), int(m[2] or 1)) if m else None


def fmt_month(value, t) -> str:
    d = ym(value)
    return f"{t['months'][d[1] - 1]} {d[0]}" if d else ""


def fmt_range(start, end, t) -> str:
    a, b = fmt_month(start, t), (fmt_month(end, t) if end else t["present"])
    return f"{a} – {b}" if a else b


def short_url(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").rstrip("/")


def has_any(tags, wanted) -> int:
    return len(set(tags or []) & set(wanted))


# ---------- selección (perfil base + versión -> contexto) ----------

def nb(text: str | None) -> str | None:
    """Espacio no separable entre un número y su unidad («85 %», «20 min»): la cifra no se parte en dos líneas."""
    return re.sub(r"(\d) (%|min|s|h|ms|KB|MB|GB|mil)(?!\w)", lambda m: f"{m[1]}\u00a0{m[2]}", text) if text else text


def brief(h: dict, on: bool) -> dict:
    """Modo breve: usa `short` (≤ ~90 caracteres, con la cifra) si existe."""
    return {**h, "text": nb(h.get("short") if on and h.get("short") else h["text"])}


def pick_highlights(job: dict, wanted: list[str], spec: dict, skill_words: set[str]) -> list[dict]:
    """Elige logros: explícitos por índice, o por prioridad > tiene cifra > menciona habilidades de la versión > tags."""
    hls = [h if isinstance(h, dict) else {"text": h} for h in job.get("highlights") or []]
    if "highlights" in spec:
        return [hls[i] for i in spec["highlights"] if i < len(hls)]
    hls = [h for h in hls if not wanted or has_any(h.get("tags"), wanted)] or hls
    mentions = lambda h: sum(w in h["text"].lower() for w in skill_words)
    hls.sort(key=lambda h: (h.get("priority", 9), not h.get("metric"), -mentions(h), -has_any(h.get("tags"), wanted)))
    return hls[: spec.get("max", 4)]


def pick_skills(profile: dict, version: dict) -> list[dict]:
    skills = profile.get("skills", [])
    if version.get("skills"):
        skills = [s for n in version["skills"] for s in skills if s["name"] == n]
    seen = set(version.get("skills_omit", []))
    out = []
    for s in skills:                              # sin repetir una herramienta entre grupos
        kws = [k for k in s["keywords"] if k not in seen]
        seen.update(kws)
        if kws:
            out.append({**s, "keywords": kws})
    return out


def build_context(profile: dict, version: dict, draft: bool, base_dir: Path) -> dict:
    t = I18N[version.get("idioma", "es")]
    wanted = version.get("tags") or OBJECTIVE_TAGS.get(version.get("objetivo"), [])
    b = profile["basics"]

    short = version.get("breve", False)
    skills = pick_skills(profile, version)
    skill_words = {k.split(" (")[0].lower() for s in skills for k in s["keywords"]}

    jobs = {w["id"]: w for w in profile.get("work", [])}
    work = []
    for spec in version.get("work") or [{"id": i} for i in jobs]:
        spec = spec if isinstance(spec, dict) else {"id": spec}
        w = jobs[spec["id"]]
        work.append({
            "id": w["id"],
            "position": spec.get("position", w["position"]),
            "name": w["name"],
            "location": w.get("location"),
            "summary": spec.get("summary", w.get("summary")),
            "dates": fmt_range(w.get("startDate"), w.get("endDate"), t),
            "current": not w.get("endDate"),
            "compact": spec.get("compact", False),
            "highlights": [] if spec.get("compact") else
                          [brief(h, short) for h in pick_highlights(w, wanted, spec, skill_words)],
        })

    projects_all = {p["name"]: p for p in profile.get("projects", [])}
    pspec = version.get("projects", {})
    if isinstance(pspec, list):                   # nombres, o {name, max} para fijar cuántos logros muestra
        chosen = [{**projects_all[x["name"]], "_max": x.get("max")} if isinstance(x, dict) else projects_all[x]
                  for x in pspec]
    else:
        chosen = sorted(projects_all.values(), key=lambda p: -has_any(p.get("tags"), wanted))[: pspec.get("max", 2)]
    pmax = version.get("project_highlights", 0)   # logros por proyecto (0 = solo descripción)
    projects = [{**p, "description": nb((p.get("short") if short else None) or p["description"]), "link": p.get("url") or (f"https://github.com/{p['repos'][0]}" if p.get("public") else None),
                 "bullets": [brief(h if isinstance(h, dict) else {"text": h}, short)
                             for h in p.get("highlights") or []][: pmax if p.get("_max") is None else p["_max"]]}
                for p in chosen]

    education = []
    for e in profile.get("education", []):
        dates = fmt_range(e.get("startDate"), e.get("endDate"), t)
        if e.get("status") == "en_curso" and e.get("endDate"):
            dates = f"{fmt_month(e['startDate'], t)} – {t['expected']} {ym(e['endDate'])[0]}"
        title = e.get("title") or " en ".join(x for x in [e.get("studyType"), e.get("area")] if x)
        education.append({"title": title, "institution": e["institution"], "dates": dates})

    # Certificaciones: las `always` primero, después las que calzan con el objetivo; las más recientes ganan.
    certs = sorted(profile.get("certificates", []), key=lambda c: str(c.get("date") or ""), reverse=True)
    certs.sort(key=lambda c: (not c.get("always"), -has_any(c.get("tags"), wanted)))   # sort estable
    certs = [c for c in certs if c.get("always") or has_any(c.get("tags"), wanted)] or certs
    certificates = [{**c, "date": fmt_month(c.get("date"), t)} for c in certs]
    languages = [{"language": l["language"],
                  "level": l["fluency"].lower() + (f" ({l['cefr']})" if l.get("cefr") else "")}
                 for l in profile.get("languages", [])]

    loc = b.get("location", {})
    photo = None
    if version.get("foto", version.get("pais", "CL") != "CL") and b.get("image"):
        photo = (base_dir / b["image"]).resolve().as_uri()

    return {
        "t": t, "b": b, "draft": draft, "photo": photo,
        "label": version.get("label", b.get("label")),
        "summary": nb(version.get("summary", b.get("summary"))),
        "location": loc.get("city"),
        "sections_main": version.get("secciones", DEFAULT_SECTIONS),
        "sections_side": version.get("secciones_lateral", []),
        "sections": version.get("secciones", DEFAULT_SECTIONS) + version.get("secciones_lateral", []),
        "work": work, "projects": projects, "skills": skills, "education": education,
        "certificates": certificates[: version.get("max_certificates", 3)], "languages": languages,
    }


def to_json_resume(ctx: dict, profile: dict) -> dict:
    """Exporta lo que se mostró como JSON Resume estándar (sin extensiones)."""
    b = copy.deepcopy(profile["basics"])
    b.pop("fullName", None)
    b["label"], b["summary"] = ctx["label"], ctx["summary"]
    jobs = {w["id"]: w for w in profile["work"]}
    work = []
    for w in ctx["work"]:
        src = jobs[w["id"]]
        work.append({"name": w["name"], "position": w["position"], "startDate": src.get("startDate"),
                     "endDate": src.get("endDate"), "summary": w.get("summary"),
                     "highlights": [h["text"] for h in w["highlights"]]})
    return {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": b, "work": work,
        "projects": [{"name": p["name"], "description": p["description"], "keywords": p.get("keywords", []),
                      **({"url": p["link"]} if p.get("link") else {})} for p in ctx["projects"]],
        "skills": [{"name": s["name"], "keywords": s["keywords"]} for s in ctx["skills"]],
        "education": [{"institution": e["institution"], "area": e.get("area"), "studyType": e.get("studyType"),
                       "startDate": e.get("startDate"), "endDate": e.get("endDate")} for e in profile["education"]],
        "certificates": [{"name": c["name"], "issuer": c.get("issuer"), "date": c.get("date")} for c in profile["certificates"]],
        "languages": [{"language": l["language"], "fluency": l["fluency"]} for l in profile["languages"]],
    }


# ---------- chequeos ----------

def check(pdf: Path, ctx: dict, version: dict) -> list[str]:
    doc = pymupdf.open(pdf)
    text = "\n".join(p.get_text() for p in doc)
    notes = []
    max_pages = version.get("paginas_max", 1)
    notes.append(f"{'OK ' if doc.page_count <= max_pages else 'ERROR'} páginas: {doc.page_count} (máximo {max_pages})")

    # Orden de lectura: nombre primero y secciones en el orden pedido.
    lines = [l.strip().lower() for l in text.splitlines() if l.strip()]
    first = lines[0] if lines else ""
    notes.append(f"{'OK ' if first == ctx['b']['name'].lower() else 'ERROR'} primera línea del texto extraído: «{first}»")
    t = ctx["t"]
    heads = [t[s] for s in ctx["sections"] if ctx.get(s)]
    # Cada título como línea propia y, después de él, una muestra de su contenido (antes del título siguiente).
    sample = {"work": lambda: ctx["work"][0]["position"], "projects": lambda: ctx["projects"][0]["name"],
              "skills": lambda: ctx["skills"][0]["keywords"][0], "education": lambda: ctx["education"][0]["institution"],
              "certificates": lambda: ctx["certificates"][0]["name"], "languages": lambda: ctx["languages"][0]["language"]}
    def find(fragment, start=0):
        frag = fragment.lower()[:22]
        return next((i for i in range(start, len(lines)) if frag in lines[i]), -1)
    seq = [0]                                     # el nombre
    for s_ in [s_ for s_ in ctx["sections"] if ctx.get(s_)]:
        h = t[s_].lower()
        seq.append(lines.index(h) if h in lines else -1)
        seq.append(find(sample[s_](), max(seq[-1], 0)) if seq[-1] >= 0 else -1)
    ok = all(p >= 0 for p in seq) and seq == sorted(seq)
    notes.append(f"{'OK ' if ok else 'ERROR'} orden de lectura (título y contenido de cada sección): {' > '.join(heads)}")

    # Contenido.
    missing = [h["text"][:60] for w in ctx["work"] for h in w["highlights"] if not h.get("metric")]
    if missing:
        notes.append(f"AVISO {len(missing)} logro(s) sin cifra, p. ej. «{missing[0]}…»")
    empty = [w["position"] for w in ctx["work"] if not w["compact"] and not w["highlights"]]
    if empty:
        notes.append(f"AVISO cargos sin logros: {', '.join(empty)}")
    shown = " ".join(h["text"] for w in ctx["work"] for h in w["highlights"]).lower()
    shown += " ".join(" ".join(p.get("keywords", [])) + p["description"] for p in ctx["projects"]).lower()
    orphan = [k for g in ctx["skills"] for k in g["keywords"] if k.split(" (")[0].lower() not in shown]
    if orphan:
        notes.append(f"AVISO habilidades que no aparecen en ningún logro o proyecto: {', '.join(orphan)}")
    contact = [ctx["b"].get("email"), ctx["b"].get("phone")] + [short_url(p["url"]) for p in ctx["b"].get("profiles") or []]
    cut = [c for c in contact if c and not any(c.lower() in l for l in lines)]
    notes.append(f"{'OK ' if not cut else 'ERROR'} contacto en una línea cada uno" + (f": se corta {', '.join(cut)}" if cut else ""))
    links = sorted({l.get("uri", "") for p in doc for l in p.get_links() if l.get("uri")})
    notes.append(f"{'OK ' if links else 'AVISO'} links clickeables en el PDF: {len(links)} ({', '.join(short_url(u) for u in links)})")
    if version.get("pais", "CL") == "CL" and re.search(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b", text):
        notes.append("ERROR el texto parece incluir un RUT")
    return notes


# Si el contenido se pasa del alto de la(s) página(s), achica las variables de tamaño en pasos de 3 %, hasta 94 %.
# Más abajo el texto queda bajo 8,5 pt: ahí corresponde recortar contenido, no la letra.
FIT_JS = """(pages) => {
  const MM = 96 / 25.4, limit = (pages * 297 - 3) * MM;   // 3 mm de margen: el PDF pagina un poco distinto que la pantalla
  const root = document.documentElement, page = document.querySelector('.page');
  const cs = getComputedStyle(root), padB = 10 * MM;   // margen inferior mínimo bajo el último texto
  const vars = ['--s-name', '--s-label', '--s-h2', '--s-h3', '--s-body', '--s-small', '--gap'];
  const base = Object.fromEntries(vars.map(v => [v, cs.getPropertyValue(v).trim()]));
  const leaves = page.querySelectorAll('h1, h2, h3, p, li, img');
  const bottom = () => Math.max(...[...leaves].map(e => e.getBoundingClientRect().bottom)) + padB;
  let f = 1;
  while (bottom() > limit && f > 0.94 + 1e-9) {
    f = Math.round((f - 0.03) * 100) / 100;
    for (const v of vars) {
      const m = base[v].match(/^([\\d.]+)(\\w+)$/);
      root.style.setProperty(v, (parseFloat(m[1]) * f).toFixed(2) + m[2]);
    }
  }
  return f;
}"""


# ---------- temas (templates/temas.yaml) ----------

def load_themes() -> dict:
    return yaml.safe_load((TEMPLATES / "temas.yaml").read_text(encoding="utf-8"))


def list_templates() -> list[str]:
    return sorted(d.name for d in TEMPLATES.iterdir() if (d / "cv.html.j2").exists())


def pick_theme(plantilla: str, version: dict) -> dict:
    """Paleta + fuentes + escala: por_defecto de la plantilla, pisado por `tema` de la versión."""
    themes = load_themes()
    sel = {**themes["por_defecto"].get(plantilla, {"paleta": "marino", "fuentes": "grotesca"}), **(version.get("tema") or {})}
    for key, pool in (("paleta", "paletas"), ("fuentes", "fuentes")):
        if sel[key] not in themes[pool]:
            raise SystemExit(f"ERROR tema.{key} «{sel[key]}» no existe en templates/temas.yaml ({', '.join(themes[pool])})")
    return {"paleta": sel["paleta"], "fuentes": sel["fuentes"], "escala": float(sel.get("escala", 1)),
            "pal": themes["paletas"][sel["paleta"]], "fu": themes["fuentes"][sel["fuentes"]]}


def theme_css(theme: dict) -> str:
    """@font-face del par elegido + bloque :root con las variables --c-* y --f-* (va al final del CSS)."""
    fonts_uri = (TEMPLATES / "fonts").as_uri()
    faces, fu = [], theme["fu"]
    for role in ("head", "body"):
        for f in fu[role]["archivos"]:
            faces.append(f'@font-face {{ font-family: "{fu[role]["familia"]}"; src: url("{fonts_uri}/{f["archivo"]}"); '
                         f'font-weight: {f["peso"]}; font-style: {f.get("estilo", "normal")}; }}')
    pal = theme["pal"]
    colors = " ".join(f"--c-{k}: {pal[k]};" for k in ("primary", "secondary", "soft", "ink", "muted", "rule", "paper", "panel"))
    head, body = fu["head"]["familia"], fu["body"]["familia"]
    return (f"\n/* Tema: paleta «{theme['paleta']}», fuentes «{theme['fuentes']}» (templates/temas.yaml) */\n"
            + "\n".join(faces) + "\n:root { " + colors
            + f' --f-head: "{head}", Arial, sans-serif; --f-body: "{body}", Arial, sans-serif;'
            + f" --head-transform: {fu['head_transform']}; --head-tracking: {fu['head_tracking']};"
            + f" --head-weight: {fu['head_weight']}; }}\n")


def build_css(tpl_dir: Path, theme: dict) -> str:
    css = (tpl_dir / "style.css").read_text(encoding="utf-8")
    if theme["escala"] != 1:                     # escala inicial de los tamaños --s-* y --gap
        css = re.sub(r"(--(?:s-[a-z]+|gap):\s*)([\d.]+)(\w+)",
                     lambda m: f"{m[1]}{float(m[2]) * theme['escala']:.2f}{m[3]}", css)
    css = css.replace('url("../fonts/', f'url("{(TEMPLATES / "fonts").as_uri()}/')

    def own_resource(m: re.Match) -> str:       # recursos de la plantilla; los SVG se colorean con el tema
        f = tpl_dir / m[1]
        if f.suffix == ".svg":
            svg = f.read_text(encoding="utf-8")
            for k in ("primary", "secondary", "soft", "paper", "panel", "ink"):
                svg = svg.replace("{%s}" % k, theme["pal"][k])
            return 'url("data:image/svg+xml;base64,%s")' % base64.b64encode(svg.encode()).decode()
        return f'url("{f.as_uri()}")'
    css = re.sub(r'url\("\./([^"]+)"\)', own_resource, css)
    return css + theme_css(theme)


def validate(vpath: Path) -> bool:
    """Corre validar.py (esquema + ids cruzados). Devuelve False si hay ERROR y muestra esas líneas."""
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "validar.py"), str(vpath)],
                       capture_output=True, text=True, encoding="utf-8")
    for line in (r.stdout + r.stderr).splitlines():
        if "ERROR" in line[:12]:
            print(line)
    return r.returncode == 0


# ---------- main ----------

def main() -> None:
    ap = argparse.ArgumentParser(description="Genera un CV (HTML, PDF, PNG y JSON Resume) desde un perfil y una versión.")
    ap.add_argument("version", type=Path, nargs="?")
    ap.add_argument("--borrador", action="store_true", help="marca en amarillo lo que falta")
    ap.add_argument("--solo-html", action="store_true", help="solo el HTML (vista previa rápida, sin PDF ni chequeo)")
    ap.add_argument("--json", action="store_true", help="imprime el resultado como JSON (para el estudio)")
    ap.add_argument("--listar", action="store_true", help="imprime plantillas, paletas y fuentes disponibles (JSON)")
    ap.add_argument("--sin-validar", action="store_true", help="no correr validar.py antes")
    args = ap.parse_args()

    if args.listar:
        th = load_themes()
        print(json.dumps({"plantillas": list_templates(),
                          "paletas": {k: v["nombre"] for k, v in th["paletas"].items()},
                          "fuentes": {k: v["nombre"] for k, v in th["fuentes"].items()},
                          "por_defecto": th["por_defecto"]}, ensure_ascii=False, indent=2))
        return
    if not args.version:
        ap.error("falta la versión (perfiles/<persona>/cvs/<version>.yaml)")

    vpath = args.version.resolve()
    if not args.sin_validar and not args.solo_html and not validate(vpath):
        raise SystemExit("ERROR validar.py encontró errores: corrígelos o usa --sin-validar")
    person_dir = vpath.parent.parent
    profile = yaml.safe_load((person_dir / "perfil.yaml").read_text(encoding="utf-8"))
    version = yaml.safe_load(vpath.read_text(encoding="utf-8"))
    ctx = build_context(profile, version, args.borrador, person_dir)

    plantilla = version.get("plantilla", "ruta")
    tpl_dir = TEMPLATES / plantilla
    theme = pick_theme(plantilla, version)
    env = Environment(loader=FileSystemLoader([tpl_dir, TEMPLATES]), autoescape=select_autoescape(["html", "j2"]))
    env.filters["short"] = short_url
    html = env.get_template("cv.html.j2").render(css=build_css(tpl_dir, theme), **ctx)

    out = vpath.parent / "salida"
    out.mkdir(exist_ok=True)
    stem = vpath.stem + ("-borrador" if args.borrador else "")
    html_path, pdf_path, png_path = (out / f"{stem}.{ext}" for ext in ("html", "pdf", "png"))
    html_path.write_text(html, encoding="utf-8")
    if args.solo_html:
        print(json.dumps({"html": str(html_path)}) if args.json else f"HTML: {html_path}")
        return
    (out / f"{vpath.stem}.json").write_text(json.dumps(to_json_resume(ctx, profile), ensure_ascii=False, indent=2, default=str),
                                             encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
        page.goto(html_path.as_uri())
        page.evaluate("document.fonts.ready")
        fit = page.evaluate(FIT_JS, version.get("paginas_max", 1))
        page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True)
        page.screenshot(path=str(png_path), full_page=True)
        browser.close()

    # Copia con nombre legible para subir a LinkedIn o a un portal: «<perfil> - <nombre>.pdf» (el perfil va primero
    # porque LinkedIn corta el nombre del archivo y así se distingue cuál es cuál).
    if not args.borrador:
        legible = re.sub(r'[<>:"/\|?*]', "", f"{ctx['label'].split('|')[0].strip()} - {ctx['b']['name']}.pdf")
        shutil.copyfile(pdf_path, out / legible)
        print(f"Para subir: {out / legible}")

    notes = check(pdf_path, ctx, version)
    if args.json:
        print(json.dumps({"html": str(html_path), "pdf": str(pdf_path), "png": str(png_path), "escala_ajuste": fit,
                          "plantilla": plantilla, "tema": {k: theme[k] for k in ("paleta", "fuentes", "escala")},
                          "chequeo": [{"nivel": n.split()[0], "texto": n.split(maxsplit=1)[1]} for n in notes]},
                         ensure_ascii=False, indent=2))
        return
    print(f"Plantilla «{plantilla}», paleta «{theme['paleta']}», fuentes «{theme['fuentes']}»")
    if fit < 1:
        print(f"Ajuste automático: tipografía y espacios al {fit:.0%} para caber en la página")
    print(f"PDF: {pdf_path}\nPNG: {png_path}")
    for line in notes:
        print(line)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

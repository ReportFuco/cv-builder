"""Valida perfiles y versiones de CV antes de renderizar.

    python validar.py                          # todas las personas en ./perfiles
    python validar.py perfiles/<persona>       # perfil.yaml + todas sus versiones
    python validar.py perfiles/<persona>/cvs/data.yaml   # una versión (y su perfil)

Revisa el JSON Schema (schema/*.schema.json) y lo que el esquema no ve: ids y nombres que la versión pide y no
existen, índices de logros fuera de rango, plantilla o foto que faltan, fechas al revés, logros sin cifra.
Imprime OK / AVISO / ERROR como render.py. Sale con código 1 si hay algún ERROR.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SKILL = Path(__file__).resolve().parent.parent
SCHEMAS = {n: json.loads((SKILL / "schema" / f"{n}.schema.json").read_text(encoding="utf-8")) for n in ("perfil", "version")}
REGISTRY = Registry().with_resources(
    [(s["$id"], Resource.from_contents(s)) for s in SCHEMAS.values()])
VALIDATORS = {n: Draft202012Validator(s, registry=REGISTRY) for n, s in SCHEMAS.items()}

SOURCE_RE = re.compile(
    r"^(cv-\d{4}|linkedin-\d{4}-\d{2}|github(:\S+)?|fuentes/\S+|entrevista(-\d{4}-\d{2}-\d{2})?|servidor|sitio:\S+)"
    r"( \+ (cv-\d{4}|linkedin-\d{4}-\d{2}|github(:\S+)?|fuentes/\S+|entrevista(-\d{4}-\d{2}-\d{2})?|servidor|sitio:\S+))*$")


def load(path: Path):
    return normalize(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def normalize(x):
    """YAML convierte 2026-09-01 en date: se pasa a texto para que el esquema lo juzgue."""
    if isinstance(x, dict):
        return {k: normalize(v) for k, v in x.items()}
    if isinstance(x, list):
        return [normalize(v) for v in x]
    if isinstance(x, (dt.date, dt.datetime)):
        return x.isoformat()
    return x


def schema_errors(kind: str, data) -> list[str]:
    out = []
    for e in sorted(VALIDATORS[kind].iter_errors(data), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in e.path) or "(raíz)"
        out.append(f"ERROR esquema en {where}: {e.message[:160]}")
    return out


def hl_list(entry: dict) -> list[dict]:
    return [h if isinstance(h, dict) else {"text": h} for h in entry.get("highlights") or []]


def walk_sources(x, found: list[str]):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "source" and isinstance(v, str):
                found.append(v)
            else:
                walk_sources(v, found)
    elif isinstance(x, list):
        for v in x:
            walk_sources(v, found)


def dupes(names) -> list[str]:
    seen, out = set(), []
    for n in names:
        if n in seen:
            out.append(n)
        seen.add(n)
    return out


# ---------- perfil ----------

def check_profile(person: Path, p: dict) -> list[str]:
    notes = schema_errors("perfil", p)

    for label, names in (("ids de work", [w.get("id") for w in p.get("work", [])]),
                         ("nombres de proyectos", [x.get("name") for x in p.get("projects", [])]),
                         ("grupos de skills", [s.get("name") for s in p.get("skills", [])])):
        if d := dupes(names):
            notes.append(f"ERROR {label} repetidos: {', '.join(map(str, d))}")

    for section in ("work", "education", "projects"):
        for e in p.get(section, []):
            a, b = str(e.get("startDate") or ""), str(e.get("endDate") or "")
            if a and b and a > b:
                notes.append(f"ERROR {section} «{e.get('id') or e.get('name') or e.get('institution')}»: startDate {a} es posterior a endDate {b}")

    img = (p.get("basics") or {}).get("image")
    if img and not (person / img).is_file():
        notes.append(f"ERROR basics.image apunta a «{img}», que no existe en {person.name}/")

    hls = [h for w in p.get("work", []) for h in hl_list(w)]
    no_metric = [h for h in hls if not h.get("metric")]
    if no_metric:
        notes.append(f"AVISO {len(no_metric)} de {len(hls)} logros de experiencia sin cifra (metric)")
    no_result = [x["name"] for x in p.get("projects", []) if not x.get("result")]
    if no_result:
        notes.append(f"AVISO proyectos sin result (no deberían mostrarse): {', '.join(no_result)}")

    sources: list[str] = []
    walk_sources(p, sources)
    odd = sorted({s for s in sources if not SOURCE_RE.match(s)})
    if odd:
        notes.append(f"AVISO {len(odd)} valor(es) de source fuera del formato estándar, p. ej. {', '.join(repr(s) for s in odd[:3])}")
    if p.get("pending"):
        notes.append(f"AVISO {len(p['pending'])} pregunta(s) abiertas en pending")
    return notes


# ---------- versión ----------

def check_version(person: Path, p: dict, v: dict) -> list[str]:
    notes = schema_errors("version", v)
    jobs = {w.get("id"): w for w in p.get("work", [])}
    projects = {x.get("name"): x for x in p.get("projects", [])}
    groups = {s.get("name"): s for s in p.get("skills", [])}

    for spec in v.get("work") or []:
        spec = spec if isinstance(spec, dict) else {"id": spec}
        job = jobs.get(spec.get("id"))
        if job is None:
            notes.append(f"ERROR work: el id «{spec.get('id')}» no existe en perfil.yaml (hay: {', '.join(map(str, jobs))})")
            continue
        n = len(hl_list(job))
        bad = [i for i in spec.get("highlights", []) if isinstance(i, int) and i >= n]
        if bad:
            notes.append(f"ERROR work «{job['id']}»: índices de logros {bad} fuera de rango (tiene {n}, desde 0)")
        if not spec.get("compact") and n == 0:
            notes.append(f"AVISO work «{job['id']}» no tiene logros: conviene compact: true")

    pspec = v.get("projects")
    if isinstance(pspec, list):
        for x in pspec:
            name = x.get("name") if isinstance(x, dict) else x
            proj = projects.get(name)
            if proj is None:
                notes.append(f"ERROR projects: «{name}» no existe en perfil.yaml")
            elif not proj.get("result"):
                notes.append(f"AVISO projects: «{name}» no tiene result (métrica, usuarios o hallazgo)")

    chosen = [groups[g] for g in v.get("skills", []) if g in groups]
    for g in v.get("skills", []):
        if g not in groups:
            notes.append(f"ERROR skills: el grupo «{g}» no existe en perfil.yaml (hay: {', '.join(groups)})")
    shown_kws = {k for s in (chosen or groups.values()) for k in s.get("keywords", [])}
    useless = [k for k in v.get("skills_omit", []) if k not in shown_kws]
    if useless:
        notes.append(f"AVISO skills_omit no oculta nada con: {', '.join(useless)}")

    tpl = SKILL / "templates" / str(v.get("plantilla", ""))
    missing = [f for f in ("cv.html.j2", "style.css") if not (tpl / f).is_file()]
    if missing:
        notes.append(f"ERROR plantilla «{v.get('plantilla')}»: falta {', '.join(missing)} en templates/")

    temas_file = SKILL / "templates" / "temas.yaml"
    if isinstance(v.get("tema"), dict) and temas_file.is_file():
        temas = yaml.safe_load(temas_file.read_text(encoding="utf-8")) or {}
        for key, pool in (("paleta", "paletas"), ("fuentes", "fuentes")):
            if key in v["tema"] and v["tema"][key] not in (temas.get(pool) or {}):
                notes.append(f"ERROR tema.{key} «{v['tema'][key]}» no existe en templates/temas.yaml "
                             f"(hay: {', '.join(temas.get(pool) or {})})")

    both = set(v.get("secciones", [])) & set(v.get("secciones_lateral", []))
    if both:
        notes.append(f"ERROR secciones repetidas en las dos columnas: {', '.join(sorted(both))}")

    img = (p.get("basics") or {}).get("image")
    if v.get("foto") and not (img and (person / img).is_file()):
        notes.append("ERROR foto: true pero el perfil no tiene una imagen válida en basics.image")

    if len(v.get("label", "")) > 90:
        notes.append(f"AVISO label largo ({len(v['label'])} caracteres): rol + 2-3 herramientas")
    if v.get("summary") and not re.search(r"\d", v["summary"]):
        notes.append("AVISO summary sin ninguna cifra: debería traer un logro y su número")
    return notes


# ---------- main ----------

def report(title: str, notes: list[str]) -> bool:
    errors = [n for n in notes if n.startswith("ERROR")]
    print(f"\n{title}")
    print("  OK  sin errores" if not errors else f"  {len(errors)} error(es)")
    for n in notes:
        print(f"  {n}")
    return not errors


def targets(args: list[str]) -> list[tuple[Path, list[Path]]]:
    """-> [(carpeta de la persona, [versiones a revisar])]."""
    if not args:
        root = Path("perfiles")
        return [(d, sorted((d / "cvs").glob("*.yaml"))) for d in sorted(root.iterdir()) if (d / "perfil.yaml").is_file()]
    out = []
    for a in map(Path, args):
        a = a.resolve()
        if a.is_dir():
            out.append((a, sorted((a / "cvs").glob("*.yaml"))))
        elif a.name == "perfil.yaml":
            out.append((a.parent, []))
        else:
            out.append((a.parent.parent, [a]))
    return out


def main() -> int:
    ok = True
    for person, versions in targets(sys.argv[1:]):
        p = load(person / "perfil.yaml")
        ok &= report(f"{person.name}/perfil.yaml", check_profile(person, p))
        for vpath in versions:
            ok &= report(f"{person.name}/cvs/{vpath.name}", check_version(person, p, load(vpath)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())

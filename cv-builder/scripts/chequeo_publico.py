"""Revisa que lo que se va a publicar en git no tenga datos personales. Pensado como hook pre-commit.

    python cv-builder/scripts/chequeo_publico.py            # revisa lo que está en el índice (git add)
    python cv-builder/scripts/chequeo_publico.py --todo     # revisa todo lo que git publicaría (versionado + nuevo)
    python cv-builder/scripts/chequeo_publico.py --instalar # lo deja como .git/hooks/pre-commit

No trae una lista de nombres escrita aquí (sería pública): saca lo sensible de los perfiles reales que hay en
perfiles/*/perfil.yaml (todos menos «ejemplo»): nombres, correos, teléfonos, usuarios y URLs de perfiles, y empresas.
Además busca patrones genéricos: RUT, teléfonos chilenos, correos que no sean de ejemplo, rutas de un PC, links de
artifacts de claude.ai y cosas con forma de clave o token. Sale con código 1 si encuentra algo.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
BINARY = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".ttf", ".otf", ".woff", ".woff2", ".ico"}

GENERIC = {
    "RUT": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"),
    "teléfono chileno": re.compile(r"\+?56\s?9[\s.-]?(?!0000)\d{4}[\s.-]?\d{4}"),   # +56 9 0000 0000 = ejemplo
    "correo real": re.compile(r"[\w.+-]+@(?!example\.(?:com|cl|org))[\w-]+\.[\w.]+"),
    "ruta de un PC": re.compile(r"[A-Za-z]:\\\\?Users\\\\?\w+|/home/\w+/|/Users/\w+/"),
    "link de artifact": re.compile(r"claude\.ai/(?:code/)?artifact/\w+"),
    "clave o token": re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
}
# Palabras de nombres de empresa demasiado comunes para bloquearlas.
COMMON = {"universidad", "grupo", "chile", "santiago", "servicios", "comercial", "empresa", "empresas", "cobranzas",
          "consultores", "ingeniería", "ingenieria", "tecnología", "tecnologia", "sociedad", "limitada", "compañía",
          "nacional", "internacional", "pontificia", "católica", "catolica", "instituto", "portales",
          "tesis", "memoria", "capstone", "proyecto", "práctica", "practica"}   # también nombres genéricos de proyecto
# Correos que sí pueden aparecer (sin datos de nadie).
ALLOWED_EMAILS = {"noreply@anthropic.com"}


def private_terms() -> dict[str, str]:
    """Términos sensibles sacados de los perfiles reales: {término en minúsculas: de dónde salió}."""
    terms: dict[str, str] = {}
    for f in (ROOT / "perfiles").glob("*/perfil.yaml"):
        if f.parent.name == "ejemplo":
            continue
        try:
            p = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        b = p.get("basics", {}) or {}
        who = f.parent.name
        for k in ("name", "fullName", "email"):
            if b.get(k):
                terms[str(b[k]).lower()] = f"{who}: basics.{k}"
        for part in str(b.get("fullName") or b.get("name") or "").split():
            if len(part) >= 5:                      # apellidos y nombres poco comunes
                terms[part.lower()] = f"{who}: parte del nombre"
        if b.get("phone"):
            terms[re.sub(r"\D", "", str(b["phone"]))[-8:]] = f"{who}: teléfono"
        for pr in b.get("profiles") or []:
            for k in ("username", "url"):
                if pr.get(k):
                    terms[str(pr[k]).lower().removeprefix("https://").removeprefix("www.")] = f"{who}: perfil {pr.get('network')}"
        for w in p.get("work") or []:
            if w.get("name"):
                terms[str(w["name"]).lower()] = f"{who}: empresa"
                for word in re.findall(r"[A-ZÁÉÍÓÚÑ][\wáéíóúñ]{5,}", str(w["name"])):   # palabra distintiva
                    if word.lower() not in COMMON:
                        terms[word.lower()] = f"{who}: empresa ({w['name']})"
            if w.get("id"):
                terms[str(w["id"]).lower()] = f"{who}: id de cargo"
        for pr in p.get("projects") or []:
            if pr.get("name"):
                name = str(pr["name"]).split("—")[0].strip().lower()
                if name not in COMMON:                                  # «Tesis — …» no identifica a nadie
                    terms[name] = f"{who}: proyecto"
            if pr.get("url"):
                host = re.sub(r"^https?://(www\.)?", "", str(pr["url"])).split("/")[0].lower()
                terms[host] = f"{who}: sitio de un proyecto"
            for repo in pr.get("repos") or []:
                terms[str(repo).lower()] = f"{who}: repo"
        terms[who.lower()] = f"{who}: nombre de la carpeta"
    extra = ROOT / ".chequeo-extra.txt"           # términos propios a bloquear; el archivo no se publica
    if extra.exists():
        for line in extra.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                terms[line.strip().lower()] = ".chequeo-extra.txt"
    return {t: s for t, s in terms.items() if len(t) >= 4}


def files_to_check(all_files: bool) -> list[Path]:
    if all_files:
        cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    else:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, encoding="utf-8").stdout
    return [ROOT / l for l in out.splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--instalar", action="store_true")
    args = ap.parse_args()

    if args.instalar:
        hook = ROOT / ".git" / "hooks" / "pre-commit"
        hook.write_text('#!/bin/sh\npython cv-builder/scripts/chequeo_publico.py || exit 1\n', encoding="utf-8")
        print(f"Instalado: {hook}")
        return 0

    terms = private_terms()
    problems = []
    for f in files_to_check(args.todo):
        rel = f.relative_to(ROOT).as_posix()
        for t, src in terms.items():                # el nombre del archivo también cuenta
            if t in rel.lower():
                problems.append(f"{rel}: el nombre del archivo contiene un dato de {src}")
        if f.suffix.lower() in BINARY or not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        low = text.lower()
        for n, line in enumerate(low.splitlines(), 1):
            for t, src in terms.items():
                if t in line:
                    problems.append(f"{rel}:{n}: dato de {src}")
        for label, rx in GENERIC.items():
            for m in rx.finditer(text):
                if label == "correo real" and m.group(0).lower() in ALLOWED_EMAILS:
                    continue
                n = text.count("\n", 0, m.start()) + 1
                problems.append(f"{rel}:{n}: {label}")

    if problems:
        print("NO PUBLICAR: hay datos que parecen personales o secretos:")
        for p in sorted(set(problems)):
            print("  " + p)
        print(f"({len(set(problems))} hallazgos; si alguno es falso positivo, cambia el texto por un ejemplo genérico)")
        return 1
    print(f"OK: {len(terms)} términos privados y {len(GENERIC)} patrones revisados, sin hallazgos.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

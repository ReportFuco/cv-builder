"""Crea la carpeta de una persona nueva, o una versión nueva, desde las plantillas de schema/plantillas/.

    python nuevo_perfil.py <persona>                    # perfiles/<persona>/{perfil.yaml, fuentes/, cvs/}
    python nuevo_perfil.py <persona> --version data     # perfiles/<persona>/cvs/data.yaml

<persona> va en minúsculas y sin tildes (camila, juan-perez). Nunca sobrescribe un archivo existente.
Se corre desde la raíz del proyecto (donde está perfiles/).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PLANTILLAS = Path(__file__).resolve().parent.parent / "schema" / "plantillas"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def copy(src: Path, dst: Path, replace: dict[str, str] | None = None) -> None:
    if dst.exists():
        print(f"Ya existe, no se toca: {dst}")
        return
    text = src.read_text(encoding="utf-8")
    for k, v in (replace or {}).items():
        text = text.replace(k, v)
    dst.write_text(text, encoding="utf-8")
    print(f"Creado: {dst}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("persona")
    ap.add_argument("--version", help="objetivo de la versión a crear (data, desarrollo, ...)")
    a = ap.parse_args()
    if not SLUG.match(a.persona):
        sys.exit(f"«{a.persona}»: usa minúsculas, números y guiones, sin tildes ni espacios.")

    person = Path("perfiles") / a.persona
    if a.version:
        if not (person / "perfil.yaml").is_file():
            sys.exit(f"No existe {person / 'perfil.yaml'}: crea primero la persona.")
        (person / "cvs").mkdir(exist_ok=True)
        copy(PLANTILLAS / "version.yaml", person / "cvs" / f"{a.version}.yaml",
             {"«<objetivo>»": f"«{a.version}»"})
        return

    for d in ("fuentes", "cvs"):
        (person / d).mkdir(parents=True, exist_ok=True)
    copy(PLANTILLAS / "perfil.yaml", person / "perfil.yaml")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()

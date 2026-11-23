# Convenciones del proyecto

Reglas para que cada sesión deje el proyecto igual de ordenado. El modelo de datos está en
`cv-builder/schema/README.md`; el flujo de la skill, en `cv-builder/SKILL.md`.

## Idioma y nombres

- Todo en **español de Chile**: documentos, comentarios, mensajes de los scripts, nombres de archivos.
- Claves de datos: las del **perfil** en inglés (vienen de JSON Resume: `work`, `highlights`, `startDate`);
  las de la **versión** en español (`objetivo`, `secciones`, `plantilla`). No mezclar dentro de cada archivo.
- Archivos y carpetas nuevos: **kebab-case, minúsculas, sin tildes ni espacios** (`logros-distribuidora.md`).
  Excepción: los archivos que entrega la persona (CVs en PDF, capturas) conservan su nombre.
- Persona: `perfiles/<nombre>/` (`camila`). Versión: `cvs/<objetivo>.yaml`; si hay varias del mismo objetivo,
  `cvs/<objetivo>-<empresa>.yaml` (`data-distribuidora.yaml`).
- `id` de un cargo: `<empresa>-<area>` (`distribuidora-bi`, `financiera-operaciones`).
- Capturas de referencia: `NN-<sitio>-<tema>.png`.

## Fechas

- En los datos: ISO 8601 `AAAA-MM`. Sin `endDate` = actual.
- En notas y documentos: `DD-MM-AAAA` (22-11-2026). Nunca «hoy» o «la semana pasada».

## Dónde va cada cosa

| Qué | Dónde |
|---|---|
| Datos de una persona (perfil, foto, CVs viejos, capturas, notas) | `perfiles/<persona>/` y su `fuentes/` |
| Lo que sirve para cualquier persona (scripts, plantillas, referencias, esquema) | `cv-builder/` |
| Archivos generados | `perfiles/<persona>/cvs/salida/` — se regeneran, nunca se editan a mano |
| Historial de diseño | `cvs/historial.jsonl` (una línea JSON por guardado del estudio, solo se agrega) y `cvs/salida/historial/<version>-<fecha>.png` |
| Banners de LinkedIn | `cvs/salida/banner/<version>-<estilo>.png` (y `-zonas.png`); plantilla en `cv-builder/banners/` |
| Temporales del estudio | `perfiles/<persona>/.estudio/` — se borra al cerrar el estudio |
| Propuestas para evaluar antes de implementar | `docs/propuestas/<tema>.md`, con **Estado** arriba (para evaluar · aprobada · descartada · implementada) |
| Pruebas y archivos temporales | scratchpad de la sesión, nunca en el proyecto |

La skill no puede depender de datos de una persona: nada en `cv-builder/` nombra a una persona real.

## Scripts (`cv-builder/scripts/`)

- Python 3.13. Dependencias en `requirements.txt`; si se suma una, se anota ahí.
- Docstring arriba con el uso (`python <script>.py ...`).
- Salida con prefijos `OK` / `AVISO` / `ERROR`; código de salida 1 si hay algún `ERROR`.
- `sys.stdout.reconfigure(encoding="utf-8")` (la consola de Windows rompe las tildes).
- Se corren desde la raíz del proyecto.

## Checklists

**Agregar un objetivo** (p. ej. `ventas`): fila en `cv-builder/references/objetivos.md` → `OBJECTIVE_TAGS` en
`render.py` → `enum` de `objetivo` en `schema/version.schema.json`.

**Agregar un tag**: `enum` de `tag` en `schema/perfil.schema.json` → lista en `schema/README.md` → objetivos que lo
usan en `references/objetivos.md` (y en `OBJECTIVE_TAGS`).

**Agregar una clave a la versión**: implementarla en `render.py` → `schema/version.schema.json` → tabla en
`schema/README.md` → `schema/plantillas/version.yaml` si es de uso común.

**Agregar una plantilla**: seguir `cv-builder/references/plantillas.md` y sumarla a `por_defecto` en
`templates/temas.yaml`.

**Agregar una paleta o un par de fuentes**: `templates/temas.yaml` (contraste ≥ 4,5:1; fuentes OFL en
`templates/fonts/`). El estudio y `render.py --listar` las toman solas.

**Quien cambie el diseño de una versión a mano** (no con el estudio) agrega igual una línea a `historial.jsonl` con
`quien: "<agente o persona>"`, para que el registro quede completo.

**Agregar una persona**: `python cv-builder/scripts/nuevo_perfil.py <persona>`, llenar con sus fuentes, anotarla en
`CLAUDE.md` («Personas por ahora»).

## Antes de dar algo por terminado

1. `python cv-builder/scripts/validar.py` sin `ERROR`.
2. Si cambió un perfil, una plantilla o `render.py`: renderizar todas las versiones afectadas y mirar los PNG.
3. Actualizar «Próximos pasos» en `CLAUDE.md` si se cerró un hito, y la fila propia en `COORDINACION.md`.

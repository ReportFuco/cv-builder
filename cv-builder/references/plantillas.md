# Cómo se hace una plantilla

Una plantilla es una carpeta en `templates/<nombre>/` (minúsculas, una palabra: `ruta`, `ola`) con:

| Archivo | Contenido |
|---|---|
| `cv.html.j2` | Jinja2. Recibe el contexto de `render.py` (`b`, `t`, `label`, `summary`, `work`, `projects`, `skills`, `education`, `certificates`, `languages`, `photo`, `draft`, `sections_main`, `sections_side`) y el CSS en `css`. |
| `style.css` | Fuentes con `url("../fonts/…")`; recursos propios con `url("./…")`. `render.py` los reescribe a rutas absolutas. |
| recursos | SVG u otros archivos propios (`wave.svg`). |

Colores y fuentes **no se fijan en la plantilla**: vienen del tema (`templates/temas.yaml`). `render.py` agrega al
final del CSS un `:root` con `--c-primary`, `--c-secondary`, `--c-soft`, `--c-ink`, `--c-muted`, `--c-rule`,
`--c-paper`, `--c-panel`, `--f-head`, `--f-body`, `--head-transform`, `--head-tracking` y `--head-weight` (con sus
`@font-face`). La plantilla usa solo esas variables y define en su propio `:root` valores de respaldo. Una plantilla
nueva se suma a `por_defecto` en `temas.yaml`.

Las fuentes van en `templates/fonts/`, archivos locales con su licencia OFL al lado (`OFL-<Familia>.txt`). Nada se
carga desde internet: el render tiene que funcionar sin conexión.

## Reglas ATS (las verifica `render.py` al final)

1. **Orden del HTML = orden de lectura.** Nombre (`<h1>`) primero, después titular, perfil, secciones principales y
   al final la columna lateral. La posición visual se resuelve con CSS grid/flex, nunca reordenando el HTML.
2. **Nada que tenga texto lleva `position`** (absolute, relative con desplazamiento, fixed): Chrome lo escribe al final
   del PDF y rompe el orden. Solo decoración sin texto (foto, ola, fondos) puede ir posicionada.
3. Cada título de sección es un `<h2>` con el texto exacto de `t[<sección>]` en una línea propia («Experiencia»).
4. Texto real y seleccionable: nada de texto en imágenes ni en SVG. Íconos SVG inline con `aria-hidden="true"`.
5. Links como `<a href>` para que queden clickeables en el PDF.
6. A4 (`@page { size: A4; margin: 0; }`), un color de acento, sin barras ni estrellas de nivel.

## Lo que necesita el ajuste automático a la página

- Un contenedor `.page`.
- Tamaños en variables CSS en `:root`: `--s-name`, `--s-label`, `--s-h2`, `--s-h3`, `--s-body`, `--s-small`, `--gap`
  (número + unidad, p. ej. `9.4pt`). `render.py` las achica en pasos de 3 % hasta 94 %.
- El modo borrador: `body.borrador` resalta lo que falta (usar una variable `--mark`).

## Antes de darla por buena

Renderizar todas las versiones existentes con la plantilla, mirar los PNG y que el chequeo ATS salga sin `ERROR`.

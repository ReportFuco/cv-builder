# Modelo de datos: un perfil base por persona, muchas versiones de CV

```
perfiles/                         ← datos de las personas (FUERA de la skill; no se comparte)
└── <persona>/
    ├── perfil.yaml               ← base: TODO lo que la persona ha hecho, sin recortar
    ├── foto.jpg                  ← opcional
    ├── fuentes/                  ← CVs antiguos, capturas de LinkedIn, export de GitHub
    └── cvs/
        ├── data.yaml             ← una versión = objetivo + selección + redacción
        ├── desarrollo.yaml
        └── salida/               ← JSON Resume, HTML, PDF y PNG generados
```

## Estándares que seguimos

| Qué | Estándar | Por qué |
|---|---|---|
| Estructura del perfil | [JSON Resume](https://jsonresume.org/schema) (`basics`, `work`, `education`, `projects`, `skills`, `languages`, `certificates`) | Formato abierto conocido; la salida sirve con otras herramientas y temas |
| Fechas | ISO 8601 `AAAA-MM`; sin `endDate` = cargo actual | Sin ambigüedad; se formatean según el país al renderizar |
| Idiomas | MCER/CEFR (A1–C2) en `cefr` | «Nivel medio» no le dice nada a un reclutador |
| País | ISO 3166 (`CL`) en `countryCode` | Define foto, datos personales y formato de fechas |

## Por qué dos niveles

- **`perfil.yaml` es la única fuente de verdad.** Fechas, cargos y logros se escriben una vez. Así un mismo cargo
  no termina con tres rangos de fechas distintos en tres documentos.
- **Cada versión solo elige, ordena y redacta.** Un CV de data y uno de liderazgo usan la misma experiencia,
  pero muestran otros logros, otro titular y otro orden de secciones.

## Extensiones al JSON Resume (solo en el perfil base)

| Campo | Dónde | Para qué |
|---|---|---|
| `highlights[]` como objeto `{text, short, metric, priority, tags, source}` | `work`, `projects` | Elegir logros por objetivo y detectar los que no tienen métrica |
| `short` | logros, proyectos | Versión breve (≤ ~90 caracteres, con la cifra); la usan las versiones con `breve: true` |
| `metric` | logros | La cifra. `null` = falta: el validador y el render lo avisan |
| `priority` | logros | 1 = el más fuerte; desempata cuando hay más logros que espacio |
| `tags[]` | logros, proyectos, certificados, grupos de skills | Vocabulario cerrado: `data`, `automatizacion`, `desarrollo`, `procesos`, `logistica`, `liderazgo`, `ia`, `gestion`, `infraestructura`, `seguridad` |
| `source` | cualquier entrada | De dónde salió el dato (formato abajo) |
| `id` | `work` | kebab-case sin tildes (`distribuidora-bi`); las versiones lo referencian |
| `fullName`, `status`, `department`, `title` | `basics`, `education`, `work` | Datos que JSON Resume no trae; `title` reemplaza «`studyType` en `area`» |
| `result` | `projects` | Obligatorio para mostrar un proyecto: métrica, usuarios o hallazgo |
| `repos[]`, `public` | `projects` | `usuario/repo`; con `public: true` y sin `url`, se enlaza el primer repo |
| `always` | `certificates` | Va en todas las versiones |
| `pending[]` | raíz | Preguntas abiertas: datos que faltan o no cuadran |

Al exportar una versión, los `highlights` pasan a texto y se quitan las extensiones → JSON Resume válido.

### Formato de `source`

`cv-AAAA` (CV antiguo) · `linkedin-AAAA-MM` (captura o export) · `github:<repo>` · `fuentes/<archivo>` (notas en la
carpeta de la persona) · `entrevista-AAAA-MM-DD` (lo dijo la persona) · `servidor` · `sitio:<dominio>`.
Varias fuentes se unen con ` + ` (`github:tablero-ventas + sitio:example.com`). El validador avisa los que no calzan.

## Versión de CV (`cvs/<objetivo>.yaml`)

Cada clave está implementada en `scripts/render.py`. Si se agrega una allá, se agrega en `version.schema.json` y aquí.

| Clave | Contenido |
|---|---|
| `objetivo` | uno de `references/objetivos.md`; define los tags que se priorizan |
| `tags` | opcional: reemplaza los tags del objetivo |
| `cargo_buscado`, `aviso` | cargo y, si hay, texto o URL de la oferta (palabras clave) |
| `idioma` (`es`/`en`), `pais` (ISO 3166) | presentación y formato de fechas |
| `plantilla` | carpeta de `templates/`: `ola` y `lateral` (dos columnas), `ruta` y `clasica` (una; `clasica` = máximo ATS) |
| `tema` | `{paleta, fuentes, escala}` de `templates/temas.yaml`; lo que falte sale de `por_defecto[<plantilla>]`. Lo escribe el estudio |
| `foto` | en `CL` es `false` por defecto |
| `breve` | usa `short` en logros y proyectos |
| `paginas_max` | 1 (o 2 con más de 10 años de experiencia); el render achica hasta 94 % y después avisa |
| `label`, `summary` | titular y resumen redactados para este objetivo |
| `secciones`, `secciones_lateral` | orden de la columna principal y de la lateral (`work`, `projects`, `skills`, `education`, `certificates`, `languages`) |
| `work[]` | `id`, o `{id, max, highlights: [índices], compact, position, summary}`; `compact` = una sola línea |
| `projects` | lista de nombres o de `{name, max}`; o `{max: n}` para elegir por tags |
| `project_highlights` | logros por proyecto cuando no se fija `max` (0 = solo descripción) |
| `skills`, `skills_omit` | grupos del perfil en orden; herramientas que no se muestran |
| `max_certificates` | cuántos certificados (los `always` van primero) |
| `banner` | banner de LinkedIn: `{estilo, antetitulo, titulo, herramientas, frase, cifras: [{valor, texto}], ruta, url, tema}`; todo opcional (ver `scripts/banner.py`) |

Pendiente (no implementado): `sensitive` para RUT, fecha de nacimiento o dirección cuando el aviso los exige
(universidades, sector público).

## Validación

- `schema/perfil.schema.json` y `schema/version.schema.json` (JSON Schema 2020-12). Los YAML llevan en la primera
  línea `# yaml-language-server: $schema=...` para que el editor los valide al escribir.
- `python cv-builder/scripts/validar.py [perfiles/<persona>]`: esquema + ids, nombres e índices cruzados, plantilla,
  foto, fechas, logros sin cifra. Correrlo antes de `render.py`.
- Plantillas vacías en `schema/plantillas/`; `scripts/nuevo_perfil.py` las copia.
- `validar.py` también revisa que `tema.paleta` y `tema.fuentes` existan en `templates/temas.yaml`.

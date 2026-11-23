---
name: cv-builder
description: Crea y mantiene CVs de una página, legibles por personas y por ATS, a partir de un perfil base por persona (JSON Resume extendido) y versiones por objetivo (data, desarrollo, automatización, procesos, operaciones, liderazgo, infraestructura). Renderiza HTML → PDF/PNG/JSON Resume con chequeo ATS. Activar cuando pidan hacer, mejorar, adaptar o actualizar un CV o currículum, una versión para un aviso o cargo, sumar experiencia o proyectos de GitHub/LinkedIn a un perfil, o crear el perfil de una persona nueva.
---

# cv-builder

Datos primero, render después. Cada persona tiene **un** perfil base con todo lo que ha hecho; cada CV es una
**versión** que solo elige, ordena y redacta. Nunca se escribe un dato (fecha, cargo, cifra) en una versión.

```
perfiles/<persona>/             ← en el proyecto del usuario, nunca dentro de la skill
├── perfil.yaml                 ← única fuente de verdad
├── foto.jpg                    ← opcional
├── fuentes/                    ← CVs antiguos, capturas de LinkedIn, notas (<tema>.md)
└── cvs/<objetivo>.yaml         ← versiones;  cvs/salida/ ← generado, no se edita a mano
```

`<skill>` = la carpeta de este archivo. Los scripts se corren desde la raíz del proyecto (donde está `perfiles/`).

## Flujo

### 1. Preguntar (ver `references/objetivos.md`, «Preguntas de entrada»)

Siempre empieza con **«¿Qué estás buscando?»**. Después: para quién es, si hay aviso, país e idioma, qué material
hay. Con una persona que ya existe, solo se pregunta lo nuevo.

### 2. Perfil base

- Persona nueva: `python <skill>/scripts/nuevo_perfil.py <persona>` (minúsculas, sin tildes) y llenar `perfil.yaml`.
- Fuentes: CV en PDF (leer con `pymupdf`), LinkedIn **solo lo que entregue la persona** (captura, export o texto;
  nunca navegarlo), GitHub con `gh` **pidiendo permiso antes** de leer la cuenta. Guardar el material en `fuentes/`.
- Cada logro con fórmula XYZ, `short` con la cifra, `metric` (o `null`), `tags` del vocabulario y `source`.
- Si dos fuentes no coinciden, manda la más reciente y la duda va a `pending`. Recorrer `pending` con la persona.
- Modelo completo y formatos: `schema/README.md`.

### 3. Versión

- `python <skill>/scripts/nuevo_perfil.py <persona> --version <objetivo>` y completar `cvs/<objetivo>.yaml`.
- `label`, `summary`, orden de secciones y logros según la fila del objetivo en `references/objetivos.md`.
- Con aviso: sacar palabras clave y reflejarlas en `label`, `summary` y la elección de logros (sin inventar).

### 4. Validar

```
python <skill>/scripts/validar.py perfiles/<persona>
```

Corregir todo `ERROR`. Los `AVISO` (logros sin cifra, proyectos sin `result`) se convierten en preguntas para la
persona, no se rellenan inventando.

### 5. Renderizar

```
python <skill>/scripts/render.py perfiles/<persona>/cvs/<objetivo>.yaml [--borrador]
```

Genera en `cvs/salida/`: `.html`, `.pdf`, `.png` y `.json` (JSON Resume puro). `--borrador` marca en amarillo lo
que falta. Si no cabe en `paginas_max`, achica hasta 94 % y avisa: ahí se recorta contenido, no la letra.

### 5b. Ajustar el diseño (opcional, con la persona)

```
python <skill>/scripts/estudio.py perfiles/<persona>/cvs/<objetivo>.yaml
```

Abre una página local con vista previa en vivo: plantilla, paleta, fuentes, escala, foto y logros breves, con el
chequeo ATS al lado. «Guardar» escribe solo `plantilla`, `tema`, `foto` y `breve` en el YAML y genera el PDF.

### 5c. Banner de LinkedIn (opcional)

```
python <skill>/scripts/banner.py perfiles/<persona>/cvs/<objetivo>.yaml [--estilo cifras|ruta|frase|formas]
```

1584 × 396 con el mismo tema del CV, en `cvs/salida/banner/` (`<version>-<estilo>.png` para subir, al doble de
resolución, y `-zonas.png` marcando lo que tapa la foto de perfil). Estilos: **cifras** (3 logros con número),
**ruta** (trayectoria por empresa), **frase** (el resumen) y **formas** (barras redondeadas con degradé, antetítulo con la empresa). Las cifras se escriben en `banner.cifras` de la versión
tomándolas del perfil (el script sugiere candidatas): nunca se inventan. El chequeo marca texto bajo la foto,
en los bordes que recorta el celular, cortado o menor a 22 px.

### 6. Revisar

- Mirar el PNG (no solo confiar en el chequeo) y leer el chequeo ATS: primera línea = nombre, secciones en orden,
  páginas, links, habilidades huérfanas, RUT.
- Ortografía y tildes de todo el texto visible.
- Mostrar el resultado a la persona y repetir 3-6 con sus cambios.

## Historial (lo que cambió la persona)

Cada guardado del estudio agrega una línea a `perfiles/<persona>/cvs/historial.jsonl`
(`{fecha, version, quien, antes, despues, png}`) y deja la imagen en `cvs/salida/historial/`. **Al retomar una
persona, leer las últimas líneas del historial** y mirar el PNG antes de tocar el diseño: ahí está lo que eligió.

## Reglas de contenido

- Una página; 3-5 logros en el cargo actual, 1-3 en los anteriores; cargos irrelevantes en una línea (`compact`).
- Impacto antes que tecnología: qué mejoró y cuánto, con base («de 6 h a 25 min»). La herramienta va como contexto.
- Cada habilidad listada aparece en algún logro o proyecto. Sin niveles, barras ni estrellas.
- Chile: sin foto por defecto; nunca RUT, edad, estado civil, nacionalidad ni dirección (solo comuna).
- No inventar cifras. Si es confidencial: rango, % o volumen.

## Referencias

| Archivo | Cuándo leerlo |
|---|---|
| `references/objetivos.md` | Siempre: preguntas de entrada y qué cambia por objetivo |
| `schema/README.md` | Al escribir o editar `perfil.yaml` o una versión |
| `references/referencias-web.md` | Dudas de buenas prácticas (ATS, largo, orden, redacción) |
| `references/analisis-cvs-propios.md` | Ejemplo de diagnóstico de un CV existente |
| `references/plantillas.md` | Al crear o cambiar una plantilla en `templates/` (reglas ATS y de ajuste) |

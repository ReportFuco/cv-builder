# Entrevista: preguntar apenas haya contexto

Un CV bueno sale de las cifras y los detalles que la persona sabe y que no están escritos en ningún documento. Por
eso, **apenas haya material de contexto de una persona** (CV antiguo, captura o export de LinkedIn, notas, repos de
GitHub, una descripción de cargo), Claude lo lee entero y **la llena de preguntas** antes de redactar versiones.
Se vuelve a entrevistar cada vez que llega material nuevo.

## Cuándo

- Persona nueva: después de leer su material y armar el primer borrador de `perfil.yaml`, **antes** de las versiones.
- Persona que ya existe: cuando entrega un documento nuevo, cuando `validar.py` avisa logros sin cifra o cuando
  `pending` tiene preguntas abiertas. Al retomar una persona, revisar `pending` primero.
- Sin material todavía: no se entrevista a ciegas. Se piden los documentos (ver «Preguntas de entrada» en
  `objetivos.md`) y se pregunta después de leerlos.

## Cómo

1. **Leer todo primero y armar el borrador.** Cada logro con fórmula XYZ y `metric: null` donde falte la cifra. Las
   preguntas salen de los **huecos del borrador**, no de un cuestionario genérico: cada una sirve para completar un
   campo concreto (`metric`, `text`, `cefr`, `status`, una decisión de confidencialidad).
2. **Preguntar con `AskUserQuestion`**, con opciones para elegir; la persona siempre puede escribir otra cosa.
   - Máximo 4 preguntas por llamada: se hacen **varias rondas**. Lo normal son 2 a 4 rondas (8 a 16 preguntas).
     No quedarse corto: es mejor preguntar de más que dejar logros sin cifra.
   - Orden: primero lo que más cambia el CV (cifras de los logros del cargo actual y del objetivo principal),
     después las decisiones (confidencialidad, idioma, educación) y al final el contexto (proyectos, liderazgo).
   - Cada pregunta se entiende sola: nombra la empresa y el logro («Distribuidora: ¿cuántas horas a la semana tomaba
     armar a mano el reporte de ventas?»). Puede que la persona no vea el resto de la conversación.
   - Las opciones son **rangos** que la persona pueda contestar sin buscar datos («Menos de 5 h», «5 a 10 h»,
     «10 a 20 h», «Más de 20 h») y, cuando corresponde, **«No sé»**. En la descripción de cada opción se muestra cómo
     quedaría en el CV («En el CV: “10+ h a la semana”»).
   - `multiSelect: true` cuando caben varias respuestas (a quiénes capacitó, qué herramientas usaba).
3. **Repreguntar** cuando la respuesta es vaga o abre algo nuevo. «Lideré un proyecto» → ¿cuál?, ¿con quién?, ¿qué
   cambió? «Menos de 1 h» → ¿más o menos cuántos minutos? Nunca se escribe un logro de liderazgo, capacitación o
   impacto sin el hecho concreto detrás.
4. **Aplicar después de cada ronda** y mostrar el avance (qué logro cambió y cómo quedó), para que la persona vea
   para qué sirvió responder.

## Cómo se escriben las respuestas

- **Rango → piso honesto**: «10 a 30 personas» → «más de 10»; «5 a 10 h» → «5+ h a la semana». Nunca el techo.
- **«No sé»** → `metric: null` y la pregunta queda en `pending`.
- `source: entrevista-AAAA-MM-DD` y un comentario con la respuesta tal cual (`# la persona (23-11-2026): 10 a 30`).
- Una cifra que comparten dos logros va en **uno solo**, con un comentario en el otro, para no contarla dos veces si
  la versión muestra ambos.
- Una decisión de confidencialidad se aplica en `text`, `short` y `metric`, y también en el banner si lo hay.
- Lo nuevo (un logro de liderazgo, un proyecto) se agrega **al final** de la lista: así no cambian los índices que
  ya usan las versiones (`highlights: [0, 3]`).
- Al terminar, sacar de `pending` lo respondido y dejar ahí lo que quedó abierto, como pregunta lista para la
  próxima vez.

## Banco de preguntas

Se eligen según los huecos del borrador; no hay que hacerlas todas.

| Tema | Preguntas típicas | Completa |
|---|---|---|
| Volumen | ¿Cuántos registros, documentos, pedidos, causas, centros o clientes cubría? | `metric`, `text` |
| Tiempo | ¿Cuánto tomaba antes a mano y cuánto después? ¿Cada cuánto se hacía? | `metric` («de 6 h a 25 min») |
| Ahorro | ¿Cuántas horas a la semana liberó? ¿Evitó errores, multas o atrasos? | `metric` |
| Alcance | ¿Cuántas personas usaban el reporte o la herramienta? ¿Qué cargos? ¿Sigue en uso? | `text`, `metric` |
| Confidencialidad | ¿Se pueden publicar los volúmenes o solo porcentajes y tiempos? | `text`, `short`, `metric` |
| Liderazgo | ¿Coordinó personas, capacitó usuarios, lideró un proyecto, presentó a jefatura? ¿A quiénes, cuántos? | logro con tag `liderazgo` |
| Cargo y fechas | ¿Cuál es el nombre oficial del cargo? ¿Coinciden las fechas del CV y de LinkedIn? | `position`, fechas |
| Educación | ¿Titulado, egresado o en curso? ¿Cómo quiere que aparezca? | `status`, `title` |
| Idiomas | Nivel MCER (A2 básico, B1 intermedio, B2 intermedio alto, C1 avanzado); ¿tiene certificado? | `languages[].cefr` |
| Proyectos | ¿Está en producción? ¿Tiene usuarios, visitas o una URL pública? | `result`, `url` |
| Objetivo | ¿Qué versión manda primero? ¿Dónde postula? | orden de las versiones |

## Ejemplo de ronda

```
AskUserQuestion, 4 preguntas:
1. Distribuidora: ¿cuántas personas revisaban el tablero de ventas en Power BI?
   Menos de 10 · 10 a 30 (en el CV: «más de 10») · 30 a 60 · Más de 60
2. Distribuidora: antes del script, ¿cuántas horas a la semana tomaba armar el reporte a mano?
   Menos de 5 h · 5 a 10 h (en el CV: «5+ h a la semana») · 10 a 20 h · Más de 20 h
3. Financiera: ¿se pueden publicar los volúmenes (clientes, operaciones) o solo porcentajes y tiempos?
   Sí, todo · Solo porcentajes y tiempos
4. ¿Has coordinado gente, capacitado usuarios o liderado un proyecto? (varias)
   Coordiné personas · Capacité usuarios · Lideré un proyecto · No
```

Si en la 4 marca «Lideré un proyecto», la ronda siguiente pregunta cuál, con quién y qué cambió.

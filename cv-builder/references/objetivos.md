# Objetivos de CV: qué preguntar y qué cambia en cada uno

La skill abre siempre con **«¿Qué estás buscando?»**. La respuesta elige uno de estos objetivos (o dos, si la persona
quiere versiones paralelas). Cada objetivo define qué se destaca; los datos salen siempre del mismo `perfil.yaml`.

| Objetivo | Para cargos como | Qué va arriba | Logros que se eligen (tags) | Habilidades primero | Proyectos |
|---|---|---|---|---|---|
| `data` | Data Analyst, BI Analyst, Analytics | Resumen + stack de datos | `data`, `automatizacion` con métrica | SQL, Python/Pandas, Power BI, modelado | Dashboards, análisis, pipelines |
| `desarrollo` | Developer, Software Engineer jr/ssr | Stack + proyectos | `desarrollo`, `automatizacion`, `ia` | Lenguajes, frameworks, Git, APIs | Repos con link, en lo alto de la página |
| `automatizacion` | RPA / Automation, Mejora continua | Resumen con horas ahorradas | `automatizacion`, `procesos` | Python, scripting, integraciones, IA | Bots, scripts, integraciones |
| `procesos` | Analista de procesos, Control de gestión | Resumen orientado a eficiencia | `procesos`, `gestion`, `data` | Excel, BI, BPM, KPIs | Pocos; mejoras con impacto |
| `operaciones` | Logística, Torre de control, Supply chain | Experiencia operativa | `logistica`, `procesos` | ERP/WMS, KPIs operativos, Excel | Opcional |
| `liderazgo` | Jefatura, Coordinación, Team lead | Resumen de gestión de personas | `liderazgo`, `gestion` | Blandas demostradas con hechos | Solo si muestran liderazgo |
| `infraestructura` | Backend/DevOps, SRE jr, Administrador de sistemas | Stack de servidores + plataforma que opera | `infraestructura`, `seguridad`, `desarrollo` | Linux, nginx, Docker, CI/CD, bases de datos, seguridad | Lo que está en producción: servicios, dominios, tráfico, incidentes |

## Reglas comunes a todos los objetivos (fuentes en `referencias-web.md`)

- **Una página** (dos como máximo, con más de 10 años de experiencia). Una columna de lectura y un color de acento.
- **Orden**: encabezado → resumen (2-4 líneas, con un logro y su número) → experiencia → proyectos → habilidades
  → educación → certificaciones → idiomas. En `desarrollo` y `automatizacion`, o con cambio de carrera,
  **Proyectos sube por encima de Experiencia antigua y de Educación**.
- **Titular** = rol objetivo + 2-3 herramientas: «Analista de Datos y Automatización | Python · SQL Server · Power BI».
- **Logros**: 3-5 en el cargo actual, 1-3 en los anteriores; los cargos irrelevantes van en una línea.
  Verbo en pretérito + herramienta + volumen + resultado **con base** («de 6 h a 25 min»). Si la cifra es
  confidencial: rango, % o volumen («~40.000 operaciones/semana»).
- **Habilidades** en listas por categoría, con la variante exacta («SQL Server (T-SQL)»), sin niveles.
  Cada una debe aparecer también en algún logro o proyecto.
- **Chile**: sin foto por defecto; nunca RUT, edad, estado civil, nacionalidad ni dirección exacta (solo comuna).
  Excepción: formularios de universidades y sector público.
- **Idioma**: español para empresas chilenas; versión en inglés desde el mismo perfil para multinacionales y remoto.

## Preguntas de entrada (en este orden)

1. **¿Para quién es el CV?** Persona nueva (se crea `perfiles/<persona>/`) o una que ya existe.
2. **¿Qué estás buscando?** Opciones de la tabla; se puede elegir más de una y sale una versión por cada una.
3. **¿Tienes un aviso concreto?** Si lo pegan, se sacan las palabras clave y se ajusta la versión.
4. **¿Dónde postulas y en qué idioma?** País (foto, datos personales y formato de fechas) e idioma del CV.
5. **¿Qué material tienes?** CV actual (PDF), captura o export de LinkedIn, usuario de GitHub (se pide permiso antes
   de leer la cuenta), foto.
6. **Lo que falta.** Con el material leído, entrevista en rondas (`entrevista.md`): métricas de cada logro, alcance,
   confidencialidad, liderazgo, fechas que no cuadran, cargos con nombres distintos. Lo que quede abierto va a `pending[]`.

Con un perfil que ya existe, las preguntas 1, 5 y 6 se saltan o se acortan: solo se pregunta lo nuevo.

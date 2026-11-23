# Cómo diagnosticar un CV existente

Primer paso con una persona nueva: leer su CV actual (PDF) y su LinkedIn, y anotar qué conservar y qué corregir antes de
escribir el perfil. Salen de analizar CVs reales hechos en Canva y en generadores en línea; se repiten mucho.

## 1. Extraer el texto como lo ve un ATS

```python
import pymupdf
print(pymupdf.open("cv.pdf")[0].get_text())
```

- **El nombre debe salir primero** y cada sección seguida de su contenido. Las plantillas de Canva y similares suelen
  dar «IDIOMAS / EXPERIENCIA / Nombre…»: cajas sueltas en cualquier orden. Es el problema más común y el más grave.
- Texto dentro de imágenes o íconos usados como única etiqueta: el ATS no los lee.

## 2. Contenido

| Revisar | Señal de problema | Qué hacer |
|---|---|---|
| Logros | Bullets que describen tareas («Gestión de inventarios…») | Pedir la cifra: volumen, tiempo ahorrado, %, usuarios |
| Fechas | No coinciden entre el CV y LinkedIn | Preguntar cuál es la oficial; anotar la duda en `pending` |
| Cargos | Nombre distinto en cada fuente | Igual que las fechas |
| Ortografía | Errores en verbos y tecnicismos | Corregir antes de pasar el texto al perfil |
| Datos personales | Dirección exacta, RUT, edad | Solo comuna y ciudad (Chile) |
| Idiomas | «Nivel medio» | Nivel MCER (A1–C2) o certificado |
| Habilidades blandas | «Trabajo en equipo», «Proactivo» | Sacarlas; demostrarlas en un logro |
| Proyectos | Ninguno, o sin resultado ni link | Revisar GitHub (con permiso) y sitios publicados |

## 3. Diseño

| Revisar | Señal de problema | Qué hacer |
|---|---|---|
| Barras o estrellas de habilidad | «Python ████░» | Listas por categoría, sin niveles |
| Largo | Más de una página con menos de 10 años de experiencia | Recortar logros débiles y cargos antiguos (`compact`) |
| Encabezado | Decoración que ocupa media página | Plantilla `ola` o `lateral` con alto fijo |
| Foto | Mala luz o fondo cargado | Pedir una de frente, con luz pareja y fondo claro; en Chile, sin foto por defecto |

## 4. Qué conservar

Lo que la persona ya hizo bien (titular con foco, una página, link a GitHub, una buena foto) se mantiene: así reconoce
su CV en la versión nueva y confía en el cambio.

## 5. Dónde queda

- El diagnóstico va en `perfiles/<persona>/fuentes/diagnostico.md` (privado, junto a sus otras fuentes).
- Las dudas van en `pending[]` del perfil y se convierten en preguntas para la persona.

# schema-notion.md — la base de propiedades

La base que el `cargador` llena y donde Isidora decide. Diseñada el 2026-09-12
**después** del snapshot, mirando los 1.100 avisos que trajo el `buscador`
(`runs/2026-09-12-1210-2`), no lo que se suponía que traían.

Dos reglas gobiernan esta tabla:

- **Cada columna declara quién la escribe.** Las de decisión son de Isidora y el
  sistema no las toca nunca (`CLAUDE.md` regla 3).
- **Un dato que no se observó queda vacío y se declara vacío** (regla 4). Por eso
  existe *Datos faltantes*: un vacío silencioso se confunde con un cero.

---

## Identidad y trazabilidad · las escribe el sistema

| Columna | Tipo | Quién | Para qué |
|---|---|---|---|
| **Título** | title | `cargador` | El título del aviso. Observado: máximo 60 caracteres. |
| **ID del portal** | texto | `cargador` | `MLC…`. **Es la llave.** Con esto se deduplica dentro de la corrida y entre corridas (item 12). |
| **URL** | url | `cargador` | La ficha. Es de donde el `extractor-de-ficha` saca la corredora, después de la puerta 3. |
| **Corrida** | texto | `cargador` | La carpeta de `runs/` que la vio por última vez. Ata la fila al crudo que la originó. |
| **Primera vez vista** | fecha | `cargador` | No se pisa nunca después de escrita. |
| **Última vez vista** | fecha | `cargador` | Se actualiza en cada corrida. Una propiedad que deja de aparecer se marca *desapareció* y esta fecha dice cuándo se la vio por última vez. |

## Lo observado · las escribe el sistema, salen del snapshot

| Columna | Tipo | Quién | Para qué |
|---|---|---|---|
| **Precio publicado** | número | `cargador` | El número tal como lo publicó el aviso, sin convertir. |
| **Moneda publicada** | select `UF` · `CLP` | `cargador` | Observado: 1.069 en UF y 31 en CLP. Se guarda la moneda original porque el precio homologado es un cálculo y el publicado es el hecho. |
| **Precio UF** | número | `cargador` | Homologado. Si la moneda publicada es UF, es el mismo número. |
| **UF usada** | número | `cargador` | El valor de la UF con el que se homologó. Sin esto, la fila de hoy y la de dentro de tres meses no son comparables y nadie se entera. |
| **Fecha de la UF** | fecha | `cargador` | Idem. La UF se mueve todos los días. |
| **m²** | número | `cargador` | Vacío en los 2 avisos que no lo declaran. |
| **Tipo de m²** | select `útiles` · `totales` | `cargador` | Observado: 1.092 útiles y 6 totales. **No son lo mismo** y un UF/m² que los mezcla compara dos cosas distintas. |
| **Dormitorios** | número | `cargador` | Vacío en 11 avisos. |
| **Baños** | número | `cargador` | Vacío en 10 avisos. |
| **Tipología** | select `1D1B`, `2D2B`, `3D2B`, … | `cargador` | La que usa el `analista` para agrupar. Un 1D1B no se compara contra un 2D2B. Observadas 28 tipologías; las más pobladas son 2D2B (204), 1D1B (188), 3D3B (162) y 3D2B (142). |
| **Tipo de aviso** | select `unidad` · `proyecto` | `cargador` | 5 avisos son proyectos: precio *"Desde"* y atributos en rango. Su UF/m² compara el piso de un rango contra el piso de otro y sale primero en cualquier ranking. Quedan marcados, no borrados. |
| **Datos faltantes** | multi-select `m²` · `dormitorios` · `baños` | `cargador` | Hace visible el vacío. Sin esta columna, "no lo declaró" y "nadie lo cargó" se ven igual. |

## Lo calculado · las escribe el sistema, salen del `analista` (item 06)

| Columna | Tipo | Quién | Para qué |
|---|---|---|---|
| **UF/m²** | número | `analista` | Aritmética sobre lo observado. Recalculable: `Precio UF ÷ m²`. |
| **Mediana UF/m² del grupo** | número | `analista` | La mediana de su tipología. |
| **Percentil en su grupo** | número | `analista` | **Vacío si el grupo tiene menos de 5 propiedades.** |
| **Tamaño del grupo** | número | `analista` | Es lo que hace verificable lo de arriba: percentil lleno con tamaño < 5 es rojo. |

**No hay columna de score compuesto, y no la va a haber.** Un puntaje único esconde la
decisión adentro de un número que después nadie puede discutir (`specs.md`).

Tampoco hay fórmulas de Notion: los números los escribe el `analista` y el chequeo del
item 06 los recalcula y compara. Una fórmula se recalcularía sola y el chequeo estaría
verificando a Notion contra Notion.

## Memoria entre corridas · las escribe el sistema (item 12)

| Columna | Tipo | Quién | Para qué |
|---|---|---|---|
| **Estado** | select `nueva` · `repetida` · `bajó de precio` · `desapareció` | `cargador` | Exactamente uno por propiedad. Es lo que hace que la corrida doce valga la pena: a esa altura el ranking ya no sorprende, lo que interesa es qué cambió. |
| **Precio UF anterior** | número | `cargador` | Se llena sólo cuando el precio cambió. Una propiedad que bajó queda **marcada, no sobrescrita en silencio**. |

## Las decisiones · las escribe Isidora · el sistema nunca

| Columna | Tipo | Quién | Para qué |
|---|---|---|---|
| **Aprobada para visitar** | checkbox | **Isidora** | La puerta 3. El `extractor-de-ficha` la lee — sólo la lee — y trabaja únicamente sobre las marcadas, 1 a 3. |
| **Notas** | texto | **Isidora** | Lo que le llamó la atención, lo que preguntó, lo que vio. |

El chequeo de la regla 3 (item 13) mira estas dos columnas y verifica que ninguna
corrida las haya tocado.

---

## Lo que esta base **no** tiene, a propósito

- **Ninguna columna de score compuesto.**
- **Ninguna fórmula de Notion** en las columnas que el sistema verifica.
- **Ninguna columna de contacto de la corredora.** Eso vive en `contactos.json`
  (item 09), fuera de Notion: lo escribe el agente que abre la web, y lo que lee la
  web no escribe en los sistemas propios.
- **Ningún campo de precio "estimado" o "sugerido".** Lo que no publicó el aviso no
  existe.

# schema-notion.md — la base de propiedades

La base que el `cargador` llena y donde Isidora decide. Diseñada el 2026-09-12
**después** del snapshot, mirando los 1.100 avisos que trajo el `buscador`
(`runs/2026-09-12-1210-2`), no lo que se suponía que traían.

Dos reglas gobiernan esta tabla:

- **Cada columna declara quién la escribe.** Las de decisión son de Isidora y el
  sistema no las toca nunca (`CLAUDE.md` regla 3).
- **Un dato que no se observó queda vacío y se declara vacío** (regla 4). Por eso
  existe *Datos faltantes*: un vacío silencioso se confunde con un cero.

## Dónde vive

Creada el 2026-09-12 en el espacio privado de Isidora.

| | |
|---|---|
| Página | *Departamentos para Airbnb · Providencia/Ñuñoa* — `3d948bc7-29a3-81e2-93a9-f5c19b67125e` |
| Base | *Propiedades* — `0fc8de51-b840-4be6-9c8e-6fd69ab5b20b` |
| Data source (es lo que usa el `cargador`) | `c98d2385-6f7f-4b9d-b3b1-e81746204a39` |

**Cuidado con la columna URL.** Notion reserva ese nombre para el link de la fila, así
que la propiedad quedó con el nombre interno **`userDefined:URL`**. Se ve *URL* en la
pantalla, pero el `cargador` tiene que escribirla con el nombre interno o la escritura
se pierde sin error. Es exactamente el tipo de falla que el item 05 verifica campo por
campo.

Cada columna lleva su descripción escrita en Notion, y la descripción **empieza
diciendo quién la escribe** (`sistema · cargador`, `sistema · analista`, `ISIDORA`).
Así la regla no vive sólo en este archivo: vive en la base, a la vista de cualquiera
que la abra.

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
| **Precio UF** | número | `cargador` | Homologado. Si la moneda publicada es UF, es el mismo número. **El valor de la UF con el que se convirtió y su fecha no están en esta tabla: viven en el `manifest.json` de la corrida**, y la columna *Corrida* es el link. Una fila sin eso no sería auditable; con eso, la tabla no repite en 1.100 filas un dato que es uno por corrida. |
| **m²** | número | `cargador` | Vacío en los 2 avisos que no lo declaran. |
| **Tipo de m²** | select `útiles` · `totales` | `cargador` | Observado: 1.092 útiles y 6 totales. **No son lo mismo** y un UF/m² que los mezcla compara dos cosas distintas. |
| **Dormitorios** | número | `cargador` | Vacío en 11 avisos. |
| **Baños** | número | `cargador` | Vacío en 10 avisos. |
| **Tipología** | select, formato `NDMB` | `cargador` | La que usa el `analista` para agrupar. Un 1D1B no se compara contra un 2D2B. **Las opciones no se declaran de antemano: las crea el `cargador` a medida que las observa.** En el censo del 2026-09-12 salieron 28, desde 2D2B con 204 propiedades hasta 8D4B con una sola. |
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

---

## Dos cosas que se decidieron acá y conviene no olvidar

**El valor de la UF vive en el manifest, no en la tabla.** Es un dato por corrida, no
por propiedad: repetirlo 1.100 veces no lo hace más cierto y sí más fácil de
desincronizar. La cadena que lo hace auditable es *Corrida* → `runs/<corrida>/manifest.json`.
Lo que esto compra es una tabla más flaca; lo que cuesta es que borrar una carpeta de
`runs/` deja filas que ya no se pueden auditar. Por eso el crudo es inmutable.

**La cola larga de tipologías no es un problema: es el dato.** 28 combinaciones para
1.100 propiedades, con 2D2B (204) y 1D1B (188) arriba y cosas como 8D4B con una sola
abajo. No se agrupan las raras en un "otras" — eso mezclaría justo lo que la
tipología separa. Lo que las protege es *Tamaño del grupo*: un grupo de 1 se ve como
grupo de 1 y **no reporta percentil**. Un percentil sobre cuatro propiedades es un
número que parece información y no lo es.

## Lo que esta base **no** tiene, a propósito

- **Ninguna columna de score compuesto.**
- **Ninguna fórmula de Notion** en las columnas que el sistema verifica.
- **Ninguna columna de contacto de la corredora.** Eso vive en `contactos.json`
  (item 09), fuera de Notion: lo escribe el agente que abre la web, y lo que lee la
  web no escribe en los sistemas propios.
- **Ningún campo de precio "estimado" o "sugerido".** Lo que no publicó el aviso no
  existe.

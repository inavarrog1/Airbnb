# backlog.md — plan de construcción

Diseño en `specs.md`. Reglas en `CLAUDE.md`.

**Protocolo.** Cuando llegue un prompt que cae dentro de un item, primero se avisa
`esto es el item NN — ¿lo abrimos?` y se espera. No se arranca solo. Si el prompt cae
entre dos items o en ninguno, se dice en vez de forzarlo adentro del más parecido.

**Estados:** `pendiente` → `abierto` → `en curso` → `cerrado`

Un item se cierra sólo cuando su campo `cierra si` da verde. Esos campos salen de la
definición de éxito de `specs.md`, para que el backlog y el criterio de éxito no
puedan divergir.

---

## 00 · Infraestructura del proyecto  ✅ CERRADO

```
estado:      cerrado · 2026-09-12
depende de:  —
entrega:     .venv con playwright · estructura runs/ scripts/ skills/ · .gitignore
cierra si:   `python -c "import playwright"` corre sin error ·
             chromium de /opt/pw-browsers responde ·
             runs/ está ignorada por git salvo su .gitkeep
```

Nota: los browsers de Playwright ya están en `/opt/pw-browsers`; falta sólo el
paquete de Python dentro del venv. No correr `playwright install`.

---

## 01 · Zona — confirmar el polígono  ✅ CERRADO

```
estado:      cerrado · 2026-09-12
depende de:  —
entrega:     la URL del polígono, guardada y medida en specs.md
cierra si:   la URL está en specs.md ✅ · el área real del polígono < 3 km² ✅ (2,56) ·
             el método de medición queda documentado ✅
```

Resultado: polígono de **2,56 km²**, 31 vértices, sobre Providencia/Ñuñoa.

El criterio original decía "bounding box < 3 km²" y estaba mal formulado: el box de
esta zona mide 13,25 km² y el polígono sólo el 19% de eso. Medir por el box
sobreestima cinco veces. El criterio quedó corregido a **área real del polígono**,
que se obtiene decodificando el `polygon_location` y aplicando shoelace.

Queda abierto un riesgo que hereda el item 03: a 528 avisos/km² la zona daría ~1.350
avisos contra un tope de 500. Se decidió no tocar el tope hasta tener el conteo real.

---

## 02 · Skill del scraper — decodificar la gramática del portal  ✅ CERRADO

```
estado:      cerrado · 2026-09-12
depende de:  00, 01 ✅
entrega:     .claude/skills/gramatica-del-portal/SKILL.md ✅ ·
             scripts/verificar_gramatica.py ✅
cierra si:   el skill documenta cómo se arma la URL de listado ✅ · cómo pagina ✅ ·
             qué selector tiene cada card ✅ · qué campos trae ✅ ·
             cada afirmación fue verificada abriendo la página, no asumida ✅
```

El skill se llama **`gramatica-del-portal`** y lo usan el `buscador` (item 03) y el
`extractor-de-ficha` (item 09). Cada afirmación que contiene tiene un chequeo en
`scripts/verificar_gramatica.py`, que la vuelve a correr contra el portal vivo y
devuelve verde o rojo — un skill sobre un sitio ajeno se vence solo.

**Las tres cosas que se daban por conocidas: una era falsa y dos estaban incompletas.**

- *"El portal responde 302 sin JavaScript"* — **falso**. Responde 403 al User-Agent por
  defecto de `curl` y 200 con HTML completo a cualquier UA de navegador. El listado
  entero viene servido, sin ejecutar JavaScript.
- *"La paginación empieza en 1"* — cierto, y el token es `_Desde_N` donde N es el
  índice del primer aviso: `_Desde_101` es la página 2. Pero la página trae **100
  avisos, no 48** (los 48 son de la vista lista, que además intercala tarjetas que no
  son avisos).
- *"Hay avisos en CLP y otros en UF"* — cierto y medido: **1.069 en UF y 31 en CLP**.
  El JSON embebido los declara como `CLF` y `CLP` con el precio numérico, así que no
  hay que adivinar la moneda desde un símbolo.

Y tres trampas que no estaban previstas, todas del mismo tipo — cambian el universo
sin fallar: los links de paginación que arma el portal **pierden el polígono**
(1.100 → 4.085 avisos), `_OrderId_PRICE*ASC` lo pierde y encima ignora el orden, y
`_BEDROOMS_2-2` lo ignora también. Por eso no se filtra nada en la URL.

---

## 03 · buscador — snapshot crudo  ✅ CERRADO

```
estado:      cerrado · 2026-09-12 · puerta 1 cruzada
depende de:  02 ✅
entrega:     scripts/buscador.py ✅ · runs/<fecha>/01-snapshot.json ✅ · manifest.json ✅
cierra si:   declara motivo de corte ∈ {página incompleta, tope, timeout,
             sin más páginas} ✅ · 0 IDs duplicados ✅ · 0 IDs vacíos ✅ ·
             el crudo no fue modificado después de escrito ✅ ·
             Isidora dice que el snapshot sirve (puerta 1) ✅
```

**El `cierra si` tenía un cuarto motivo faltante.** La lista original —{página
incompleta, tope, timeout}— no cubre el caso en que el censo se termina y la última
página viene **llena**, que es exactamente lo que pasa acá: el total (1.100) es
múltiplo exacto del tamaño de página (100), así que la página 11 trae 100 avisos y la
12 responde 404. Con la lista original, una corrida que trae la zona **completa** no
puede declarar un motivo válido — el criterio castigaba justo el resultado que
`specs.md` busca. Se agregó `sin más páginas` (`offset + avisos >= total`, o página
siguiente sin avisos). Mismo tipo de corrección que la del item 01: el criterio estaba
mal formulado, no el resultado.

**Dos corridas, a propósito.**

| corrida | tope | motivo de corte | avisos |
|---|---|---|---|
| `runs/2026-09-12-1210` | 500 | **tope** | 500 |
| `runs/2026-09-12-1210-2` | 2.200 | **sin más páginas** | **1.100 — censo completo** |

La primera se corrió con el tope de 500 de `specs.md` para dejar el corte por tope
observado en el manifest y no supuesto. La segunda, con el tope al doble del conteo
observado y timeout de 20 min, como manda este item para ese caso. Los 500 de la
primera son un subconjunto exacto de los 1.100 de la segunda: 0 avisos que sólo
aparezcan en la corrida corta, lo que confirma que la paginación es estable entre
corridas.

**El buscador trae por HTTP, no por navegador.** El item 02 mostró que el portal sirve
el listado completo sin ejecutar JavaScript, así que el motivo por el que el diseño
pedía navegador headless resultó falso. Queda `--navegador` como segunda vía, para la
máquina local y para el día que el portal deje de servir el HTML armado. El parseo es
el mismo para las dos.

**Qué hay adentro del snapshot** (los 1.100): 1.069 en UF y 31 en CLP · 5 proyectos
con precio "Desde" · 276 de 2 dormitorios y 366 de 3 · 2 avisos sin m² y 6 sin
dormitorios, guardados vacíos y declarados vacíos · m² mediana 104, mínimo **2**
(un aviso con 2 m² es dato del portal, no del parseo) · UF/m² mediana 94,1 con un
máximo de 2.000 que sale de ese mismo aviso.

**→ Puerta 1 cruzada el 2026-09-12:** Isidora revisó el snapshot y dijo que sirve.
El censo que pasa al item 04 es el de `runs/2026-09-12-1210-2` — 1.100 avisos.

---

## 04 · Schema de Notion y creación de la base  ✅ CERRADO

```
estado:      cerrado · 2026-09-12
depende de:  03 ✅
entrega:     la base creada en el espacio privado ✅ · el schema documentado ✅
             (schema-notion.md)
cierra si:   cada columna declara tipo y quién la escribe ✅ (las 24, y la
             descripción vive en Notion, no sólo en el repo) ·
             existe la columna de aprobación para visitar ✅ ·
             existe la columna de estado (nueva/repetida/bajó/desapareció) ✅
```

24 columnas en cinco bloques. Las de decisión son dos —**Aprobada para visitar** y
**Notas**— y el sistema no las escribe nunca; el chequeo de la regla 3 (item 13) las
mira.

**Tres columnas existen porque el snapshot las hizo necesarias**, no porque se
imaginaran antes: `Tipo de m²` (1.092 avisos declaran útiles y 6 totales, y un UF/m²
que los mezcla compara dos cosas distintas), `Datos faltantes` (2 sin m², 11 sin
dormitorios, 10 sin baños — sin esta columna "el aviso no lo declaró" y "nadie lo
cargó" se ven igual) y `Tipo de aviso` (los 5 proyectos publican precio "Desde" y
atributos en rango). Esto es lo que se ganó diseñando la base **después** del
snapshot.

**Dos decisiones que se tomaron acá:**

- **El valor de la UF y su fecha no están en la tabla: viven en el manifest de la
  corrida**, y la columna `Corrida` es el link. Es un dato por corrida, no por
  propiedad; repetirlo 1.100 veces no lo hace más cierto y sí más fácil de
  desincronizar. El costo queda anotado: borrar una carpeta de `runs/` deja filas que
  ya no se pueden auditar.
- **La cola larga de tipologías no se agrupa en un "otras".** 28 combinaciones, desde
  2D2B con 204 propiedades hasta 8D4B con una. Agruparlas mezclaría justo lo que la
  tipología separa; lo que las protege es `Tamaño del grupo`, que deja ver un grupo de
  1 como grupo de 1 — y sin percentil.

**Trampa encontrada al crear la base:** Notion reserva el nombre `URL`, así que esa
columna quedó con el nombre interno `userDefined:URL`. Se ve *URL* en pantalla, pero
el `cargador` tiene que escribirla con el nombre interno o la escritura se pierde sin
error.

---

## 05 · cargador — snapshot a Notion

```
estado:      pendiente
depende de:  04
entrega:     scripts/cargador.py · filas en Notion
cierra si:   filas en Notion == filas del snapshot post-dedup ·
             precio y m² coinciden fila por fila ·
             todo homologado a UF · 0 precios ≤ 0
```

Homologación CLP→UF con el valor y la fecha de la UF registrados en el manifest.

---

## 06 · analista — ratios y ranking

```
estado:      pendiente
depende de:  05
entrega:     scripts/analista.py · columnas de ranking en Notion
cierra si:   ratios recalculados == guardados ·
             ningún grupo de <5 propiedades reporta percentil ·
             no existe ninguna columna de score compuesto
```

Cero supuestos financieros acá: sólo aritmética sobre lo observado (UF/m², mediana,
percentil). Agrupar por tipología y ordenar dentro de cada grupo — un 1D1B no se
compara contra un 2D2B.

**→ Puerta 2.** Isidora elige el puñado que pasa al evaluador. El ranking ordena, no
elige.

---

## 07 · Supuestos propios

```
estado:      pendiente
depende de:  06
entrega:     supuestos.yaml propio, firmado y fechado
cierra si:   está firmado por Isidora con fecha ·
             las tarifas y ocupaciones salen de mirar Airbnb en la zona, no del archivo de referencia
```

El `supuestos.yaml` del taller es un punto de partida de otra persona. El archivo
mismo lo dice: *"la primera tarea seria es reemplazarlos mirando Airbnb en la zona y
firmar los propios"*.

---

## 08 · evaluador — el modelo financiero

```
estado:      pendiente
depende de:  07
entrega:     evaluador.html — un archivo, sin dependencias, abre con doble clic
cierra si:   abre sin red · los 3 números por propiedad ·
             registra el hash de supuestos.yaml usado · la UF viene con su fecha
```

Antes de escribir una línea: mostrar las fórmulas de la cuota, el flujo y el punto de
equilibrio para aprobación.

Contenido acordado:
- supuestos visibles y **editables en pantalla**
- retorno y **punto de equilibrio** en gráficos según el tiempo
- sensibilidad de la cuota mensual entre tasa y bono pie
- composición de la cuota hipotecaria
- UF actualizada desde el SII
- verificación de acceso al crédito según renta
- retorno contra tasa de descuento variable
- flujo mensual del primer año y anual por el plazo del crédito
- escenario de venta con plusvalía variable en año x, recalculando ROI y VPN
- comparación lado a lado que se recalcula al mover un supuesto

**Ordena y descarta: ocupación de equilibrio, corte 65%.**

**→ Puerta 3.** Isidora mueve los supuestos y aprueba 1–3 en Notion.

---

## 09 · extractor-de-ficha

```
estado:      pendiente
depende de:  08
entrega:     scripts/extractor.py · runs/<fecha>/contactos.json
cierra si:   una ficha por propiedad aprobada, ni una más ·
             cada contacto declara si tiene mail, teléfono o ninguno
```

Es el trabajo caro. Sólo sobre las aprobadas. Lee Notion, nunca escribe.

---

## 10 · redactor-agendador · borradores

```
estado:      pendiente
depende de:  09
entrega:     un borrador en Gmail por propiedad aprobada
cierra si:   un borrador por propiedad · **0 mails enviados** ·
             cada mensaje propone 3 horarios dentro de las ventanas y de 7 días
```

Estructura fija, redacción propia. Si hay mail, va como mail; si sólo hay teléfono,
como texto de WhatsApp listo para copiar.

---

## 11 · redactor-agendador · bloqueos de agenda

```
estado:      pendiente
depende de:  10
entrega:     un evento tentativo por visita en el calendario primary
cierra si:   100% de eventos con status tentativo · 100% con 0 invitados ·
             60 min cada uno · dentro de las ventanas · timezone America/Santiago
```

Los tres horarios propuestos salen de leer la ocupación real del calendario.

---

## 12 · Memoria entre corridas

```
estado:      pendiente
depende de:  05
entrega:     dedup por ID del portal + columna de estado en Notion
cierra si:   cada propiedad tiene exactamente un estado de
             {nueva, repetida, bajó de precio, desapareció} ·
             0 duplicados entre corridas ·
             una propiedad cuyo precio cambió queda marcada, no sobrescrita en silencio
```

---

## 13 · Validador global

```
estado:      pendiente
depende de:  11, 12
entrega:     scripts/validar.py — verde o rojo, sin opinar
cierra si:   corre todos los chequeos de los items anteriores ·
             incluye los 4 chequeos de las reglas duras ·
             falla ruidosamente: si un chequeo no pasa, el paso no cierra
```

Los cuatro chequeos que miran las reglas duras, que son los que más valen porque
verifican que el sistema **no hizo** algo:
- 0 mails enviados
- 0 eventos confirmados y 0 con invitados
- el crudo no fue modificado después de escrito
- ninguna columna de decisión de Notion escrita por el sistema

---

## 14 · Scheduler

```
estado:      pendiente
depende de:  13
entrega:     corrida automática lunes 07:00 hasta el ranking
cierra si:   corre agentes 1 a 3 sin intervención ·
             el umbral de ±40% detiene la corrida y avisa cuando salta ·
             la primera corrida (sin línea de base) para siempre ·
             nunca avanza más allá de la puerta 2
```

---

## 15 · Revisión adversarial del sistema

```
estado:      pendiente
depende de:  14
entrega:     ≥10 propuestas de mejora clasificadas por impacto
cierra si:   cada propuesta dice qué falla concreta cubre ·
             las aprobadas entran como items nuevos de este backlog
```

Buscar vulnerabilidades, puntos ciegos, límites por agente (permisos, tiempo de
acción, capacidades). Pensarlo como sistema continuo: qué memoria hace sentido
mantener entre corridas.

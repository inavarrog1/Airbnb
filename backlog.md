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

## 05 · cargador — snapshot a Notion  · en curso

```
estado:      en curso · 2026-09-12 · cargada una muestra de 100 de 1.100
depende de:  04 ✅
entrega:     scripts/cargador.py ✅ · filas en Notion ⏳ (100 de 1.100)
cierra si:   filas en Notion == filas del snapshot post-dedup ⏳ (faltan 1.000) ·
             precio y m² coinciden fila por fila ✅ (100/100, 0 diferencias) ·
             todo homologado a UF ✅ · 0 precios ≤ 0 ✅
```

**UF de 40.910,10 del 2026-09-12**, sacada del SII y contrastada contra dos tablas de
la misma página. Entra por parámetro con su fecha y su fuente, y **no tiene default**:
un default sería un número inventado. Queda en el manifest de la corrida.

**Cómo se reparte el trabajo.** La autenticación de Notion la tiene el conector MCP del
agente, no un script. Así que `cargador.py` transforma y verifica —determinista y
re-corrible— y el agente escribe las filas por MCP:

```
cargador.py            01-snapshot.json → 02-filas.json (1.100 filas)
el agente (MCP)        02-filas.json → filas en Notion
cargador.py --verificar  lo que quedó en Notion vs. lo esperado, campo por campo
```

**La muestra de 100 dio todo verde**, y se eligió con criterio: incluye **las 31 en
CLP**, que son las únicas donde el cargador hace aritmética de verdad. 0 diferencias
en precio, m², dormitorios y baños. Y 0 filas con `Aprobada para visitar` o `Notas`
escritas — la regla 3, verificada contra Notion y no contra una intención.

**Dos cosas que muerden al cargar, ambas descubiertas cargando:**

- **Notion no crea opciones de select solas.** Cargar una tipología no declarada
  devuelve `validation_error` y **rechaza el lote entero**, no la fila. Quedaron
  declaradas las 27 observadas; el `cargador` va a tener que agregar las nuevas antes
  de escribir.
- **La columna URL se llama `userDefined:URL` por dentro.** Escribirla con el nombre
  visible la pierde sin error.

**Lo que falta para cerrar: las 1.000 restantes.** Cargarlas por MCP significa que el
agente transcribe ~600 KB a mano, en once llamadas. La alternativa es un token propio
de Notion en un `.env` fuera de git, con el que `cargador.py` escribe directo por la
API: segundos en vez de un rato largo, re-corrible, y es lo que el item 14 necesita
para correr un lunes a las 07:00 sin nadie mirando. **Decisión pendiente de Isidora.**

---

## 06 · analista — ratios y ranking  · en curso

```
estado:      en curso · 2026-09-12 · calculado sobre las 190 que hay en Notion
depende de:  05 (que está a su vez incompleto: 190 filas de 1.100)
entrega:     scripts/analista.py ✅ · runs/<corrida>/05-ranking.json ✅ ·
             página "Ranking por tipología" en Notion ✅ ·
             columnas de ranking en Notion ⏳
cierra si:   ratios recalculados == guardados ✅ ·
             ningún grupo de <5 propiedades reporta percentil ✅ ·
             no existe ninguna columna de score compuesto ✅ ·
             el ranking cubre el censo completo ⏳ (cubre 190 de 1.100)
```

Cero supuestos financieros: una división, una mediana y un conteo. 183 propiedades
en el ranking, 7 declaradas afuera (5 proyectos, 2 sin tipología). 19 grupos, 9 con
percentil y 10 marcados como grupo chico.

**Dos definiciones acordadas con Isidora el 2026-09-12:**

- **El grupo es (tipología, tipo de m²)**, no sólo tipología. Mismo motivo por el que
  un 1D1B no se compara con un 2D2B: 90 m² útiles no son 90 m² totales, y un UF/m²
  que los mezcla compara dos cosas distintas.
- **El percentil es el porcentaje del grupo con UF/m² menor.** 0 = la más barata por
  m² de su tipología. Dice dónde cae en la distribución; **no dice "mejor"**.

**El chequeo que hace imposible el score compuesto:** las columnas de salida se
comparan contra una lista blanca. Cualquier columna nueva que no esté declarada pone
el chequeo en rojo. La regla deja de depender de que alguien se acuerde.

**Lo que impide cerrar el item, y no es el ranking:** las 190 filas cargadas no son
una muestra aleatoria de las 1.100 — son las primeras del orden del portal, que es
comercial. El ranking es correcto sobre lo que hay, pero *las mejores de estas 190*
no es *las mejores de la zona*. Es exactamente el sesgo contra el que advierte
`specs.md`. El item cierra cuando el 05 termine de cargar.

**Dónde quedó escrito.** El ranking completo está en la página *Ranking por tipología*
de Notion y en `runs/<corrida>/05-ranking.json`. **No** está en las columnas de cada
fila: `notion-update-page` actualiza una página por llamada, y 183 filas son 183
llamadas. Con un token propio, `analista.py` las escribe en segundos.

**→ Puerta 2.** Isidora elige el puñado que pasa al evaluador. El ranking ordena, no
elige.

---

## 07 · Supuestos propios  · bloqueado por la red

```
estado:      bloqueado · 2026-09-12 · falta el acceso a Airbnb y la firma
depende de:  06
entrega:     supuestos.yaml propio, firmado y fechado · metodo-supuestos.md ✅ ·
             arriendo del mismo polígono, observado ✅
cierra si:   está firmado por Isidora con fecha ⏳ ·
             las tarifas y ocupaciones salen de mirar Airbnb en la zona ⏳
```

**Airbnb está denegado por la política de egreso de la sesión.** `airbnb.cl`,
`airbnb.com`, `api.airbnb.com` y `airdna.co` responden **403 en el CONNECT**; también
`booking.com`, `cmfchile.cl` y `bcentral.cl`. De todo lo probado sólo llegan `sii.cl`
y `portalinmobiliario.com`. Una denegación de política no se reintenta: se reporta.
**Isidora va a habilitar `airbnb.cl` y `airbnb.com`**, y entonces se levanta la
muestra siguiendo `metodo-supuestos.md`.

**El hallazgo que no arregla habilitar el dominio: la ocupación no es observable.**
Airbnb no publica cuántas noches se vendió un departamento. Todo número de ocupación
—el del taller incluido— sale de un proxy. Decidido el 2026-09-12: **proxy
`calendario_90d`, que sobreestima** porque una noche bloqueada no es una noche
vendida. Queda declarado en el propio `supuestos.yaml`, arriba de las curvas, no en
una nota al pie:

```yaml
ocupacion_metodo:
  proxy: calendario_90d
  sesgo: sobreestima
  muestra: null          # pendiente
  observado: false
```

**Lo que sí quedó observado: el arriendo tradicional del mismo polígono.**
`runs/2026-09-12-1315-arriendo` — censo completo de **429 avisos**, corte por
**página incompleta** (el primer motivo de corte natural que se dispara en una corrida
real; el censo de venta cortaba por `sin_mas_paginas`). Medianas por tipología, en
`supuestos.yaml` bajo `arriendo_observado`, marcado `observado: true`:

| Tipología | n | mediana | en pesos |
|---|---|---|---|
| 1D1B | 196 | 17,21 UF/mes | $704.267 |
| 2D2B | 80 | 31,89 UF/mes | $1.304.623 |
| 3D3B | 33 | 45,00 UF/mes | $1.840.954 |
| 3D2B | 22 | 29,33 UF/mes | $1.199.893 |

Es el piso contra el que compite un Airbnb, y el evaluador ahora lo muestra como
control de cordura: si el resultado operacional mensual no supera al arriendo mediano
de esa tipología, la operación no se justifica — arrendarlo a un año da más y tiene
menos trabajo. **El arriendo es dato observado; el Airbnb todavía sale de supuestos**,
y el evaluador lo dice en la misma pantalla.

**Tarifa plana de 100 USD por noche · decidido por Isidora el 2026-09-12.** En vez de
la curva de 12 meses, una tarifa fija para todas las tipologías y todos los meses.
Convertida con el **dólar observado del SII: 937,17 del 2026-09-11** —el 12 es sábado
y no se publica, así que el valor queda guardado con *su* fecha— da **2,2908 UF por
noche**. La tarifa misma **no es observada**: es un supuesto declarado, y el yaml lo
dice en `tarifa.observado: false`.

Lo que se pierde al fijarla, anotado en el yaml y en la pantalla:

- **la estacionalidad.** Enero y julio valen lo mismo, y la ocupación de equilibrio
  deja de distinguir un verano bueno de un invierno malo. Es justo lo que el propio
  pedido inicial quería evitar al pedir curvas y no promedios.
- **la diferencia de ingreso entre tipologías.** Un 1D1B y un 4D4B facturan igual por
  noche, así que el grande se ve peor sólo por tener más m² que pagar.

Ese segundo efecto se ve entero en el resultado: con esta tarifa, **15 de las 183
propiedades pasan el corte de 65%, y 12 de esas 15 son 1D1B**. Ninguna de las 39
propiedades 3D3B pasa. Eso no dice que los 1D1B sean mejor negocio: dice que una
tarifa plana premia al departamento chico por construcción.

**Para desbloquear el item:** observar la tarifa (Airbnb u otra fuente) y firmar.

---

## 08 · evaluador — el modelo financiero  · en curso

```
estado:      en curso · 2026-09-12 · construido y verificado, con supuestos sin firmar
depende de:  07 (bloqueado)
entrega:     evaluador.html ✅ · plantillas/evaluador.html ✅ ·
             scripts/construir_evaluador.py ✅ · scripts/verificar_evaluador.py ✅
cierra si:   abre sin red ✅ · los 3 números por propiedad ✅ ·
             registra el hash de supuestos.yaml usado ✅ · la UF viene con su fecha ✅ ·
             los supuestos están firmados ⏳ (item 07)
```

**Las fórmulas se mostraron y se aprobaron antes de escribir una línea**, como pedía
este item. Dos decisiones que tomó Isidora el 2026-09-12:

- **El bono pie baja el crédito** (`crédito = P − pie − bono`), no sólo el desembolso.
  Es lo que hace que la matriz tasa × bono pie diga algo en sus dos ejes.
- **La tasa mensual es la equivalente compuesta** `(1+anual)^(1/12) − 1`, no la
  nominal dividida por 12. Da una cuota levemente menor, y es la que capitaliza igual
  que la tasa anual declarada.

**Cómo se verifica que los números son los que dicen las fórmulas:**
`scripts/verificar_evaluador.py` abre el archivo en un Chromium de verdad, **recalcula
la cuota, la ocupación de equilibrio y el flujo del año 1 en Python, aparte**, y las
compara contra lo que muestra la pantalla. Si el HTML y la aritmética se separan, el
chequeo se pone rojo. También verifica que no sale ninguna petición de red, que no hay
errores de JavaScript, y que mover un supuesto recalcula la pantalla.

**La UF y el "abre con doble clic" no se pueden tener los dos.** Un archivo local no
puede pedirle la UF al SII: el navegador lo bloquea por CORS, y `specs.md` pide que
abra sin red. La UF va **embebida con su fecha y su fuente** (40.910,10 del
2026-09-12, del SII) y es editable en pantalla. Actualizarla es reconstruir.

**→ Puerta 3.** Isidora mueve los supuestos y aprueba 1–3 en Notion.

---

## 09 · extractor-de-ficha  · bloqueado por la puerta 3, y con un hallazgo

```
estado:      bloqueado · 2026-09-12 · 0 propiedades aprobadas en Notion
depende de:  08
entrega:     scripts/extractor.py · runs/<fecha>/contactos.json
cierra si:   una ficha por propiedad aprobada, ni una más ·
             cada contacto declara si tiene mail, teléfono o ninguno
```

**La ficha individual no trae ni mail ni teléfono.** Sondeadas dos fichas (una de
corredora, una de particular): 0 direcciones de correo y 0 teléfonos en 562 KB de
HTML servido, contra 29 menciones de iniciar sesión. El contacto va por el formulario
del propio portal, detrás de login.

Lo que **sí** trae la ficha:

| Campo | Ejemplo |
|---|---|
| `seller_name` | `Vivaqui.com` (corredora) · `Asye8378655` (alias de particular) |
| `seller_id` | `92388263` |
| `location` | latitud y longitud · **no** la dirección de calle |

**Esto abre un caso que el diseño no contempló.** El item 10 dice *"si hay mail, va
como mail; si sólo hay teléfono, como texto de WhatsApp"*. Con esta gramática el caso
real es un tercero: **ninguno de los dos, y el canal es el formulario del portal**.
Escribir ahí es enviar algo, así que lo hace Isidora, no el sistema. El entregable
honesto pasa a ser: el nombre de la corredora, y el mensaje redactado listo para que
ella lo pegue en el canal que elija.

Queda por verificar si el teléfono aparece **después de un clic con sesión iniciada**.
Eso ya no es leer una página pública: es operar una cuenta, y necesita una decisión de
Isidora antes de intentarlo.

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

---

## 16 · Duplicados por contenido

```
estado:      pendiente
depende de:  05
entrega:     chequeo en scripts/analista.py
cierra si:   reporta los grupos de avisos con mismo precio, m² y tipología
             y distinto ID · ninguno se borra, quedan marcados
```

Propuesto y postergado el 2026-09-12. **Es el más urgente de los cuatro.** El dedup
de hoy es por ID del portal, así que dos publicaciones del mismo departamento con
IDs distintos entran las dos. Ya se vieron dos avisos idénticos de $240.000.000, 44
m², 1D1B, con IDs distintos. Si eso se repite, el censo está inflado y **todas las
medianas están corridas** — y el ranking parece igual de prolijo.

---

## 17 · Distancia a la mediana del grupo, en %

```
estado:      pendiente
depende de:  06
entrega:     columna nueva calculada por el analista
cierra si:   (UF/m² − mediana del grupo) ÷ mediana, recalculable ·
             sin percentil en grupos chicos, igual que las demás
```

Propuesto y postergado el 2026-09-12. Aritmética pura. Lee mejor que el percentil:
*"está 23% bajo la mediana de su tipología"* en vez de *"percentil 12"*.

---

## 18 · Dispersión del grupo y outliers declarados

```
estado:      pendiente
depende de:  06
entrega:     rango intercuartílico por grupo · marca de outlier por propiedad
cierra si:   ninguna propiedad se descarta: se marcan ·
             el criterio (1,5 × IQR) queda escrito y es recalculable
```

Propuesto y postergado el 2026-09-12. Contesta cuándo la mediana de un grupo
significa algo. Un grupo con un rango intercuartílico enorme no tiene un precio de
mercado, tiene una nube — y ordenar dentro de esa nube es ruido prolijo. Marcaría
sola la propiedad de 2 m² y la de 417 UF/m².

---

## 19 · UF por dormitorio, y si el precio escala con la superficie

```
estado:      pendiente
depende de:  06
entrega:     dos análisis más, sin supuestos financieros
cierra si:   ambos son recalculables desde lo observado
```

Propuesto y postergado el 2026-09-12. El UF/m² castiga a los departamentos con
terrazas y logias grandes; el UF por dormitorio es otra lente sobre el mismo dato.
Y la relación precio–superficie dentro de cada grupo dice si el m² extra se paga o
no en esa tipología.

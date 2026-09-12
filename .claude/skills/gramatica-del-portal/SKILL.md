---
name: gramatica-del-portal
description: Cómo se arma, pagina y parsea una búsqueda de Portal Inmobiliario (portalinmobiliario.com) - la URL de listado, el token de paginación, dónde vive cada campo de cada aviso y las trampas que hacen que una búsqueda devuelva silenciosamente otro universo. Usar cuando se construya o se arregle el `buscador` o el `extractor-de-ficha`, o cuando una corrida devuelva una cantidad de avisos que no cuadra.
---

# La gramática de Portal Inmobiliario

Todo lo de acá se verificó abriendo la página el **2026-09-12**. Lo que no se pudo
verificar está marcado como tal. Nada está inferido de la documentación del portal
ni de cómo suele funcionar MercadoLibre.

Para re-verificarlo: `.venv/bin/python scripts/verificar_gramatica.py` — devuelve
verde o rojo sin opinar.

---

## 1 · Cómo se arma la URL de listado

```
https://www.portalinmobiliario.com/venta/departamento/[_Desde_N][_DisplayType_M]_item*location_lat:LAT1*LAT2,lon:LON1*LON2?polygon_location=<polilínea>
```

Cinco piezas, en este orden:

| Pieza | Ejemplo | Qué hace |
|---|---|---|
| raíz | `/venta/departamento/` | operación y tipo de propiedad |
| paginación | `_Desde_101` | se omite en la página 1 (ver §2) |
| tipo de vista | `_DisplayType_M` | vista mapa: **100 avisos por página** (ver §5) |
| bounding box | `_item*location_lat:-33.43…*-33.40…,lon:-70.62…*-70.57…` | la caja que envuelve al polígono |
| polígono | `?polygon_location=n~|jEn|xmL…` | **la zona real**, como query param |

El `polygon_location` es una polilínea codificada de 31 vértices. Va **siempre**, en
todas las páginas. Sin él la búsqueda no falla: devuelve el bounding box, que es
**3,7 veces más avisos** (medido: 1.100 con polígono contra 4.085 sin polígono, misma
corrida). Ese es el modo de falla peligroso — no hay error, hay otro universo.

`_NoIndex_True` aparece en las URLs que arma el portal y **no cambia nada**: mismo
total, mismo primer aviso. Se puede omitir.

---

## 2 · Cómo pagina

**El token es `_Desde_N` y N es el índice del primer aviso, no el número de página.**

```
pagina 1  →  (sin token)        offset declarado = 0
pagina 2  →  _Desde_101         offset declarado = 100
pagina n  →  _Desde_{(n-1)*100+1}
```

La numeración **empieza en 1**. Calcular `(pagina-1)*100` en vez de `+1` corre todo
un lugar y repite un aviso por página; el deduplicado lo tapa y el censo queda corto.

Verificado en las 11 páginas del polígono: **1.100 avisos, 0 IDs duplicados, 0 IDs
vacíos**, y solapamiento cero entre páginas consecutivas y no consecutivas.

### Dónde se para

El HTML trae `"total"`, `"limit"` y `"offset"` embebidos. La condición de fin es la
primera que ocurra:

| Señal | Qué se observó |
|---|---|
| `offset >= total` | la página siguiente responde **HTTP 404** con 0 avisos |
| página con menos avisos que `limit` | no ocurrió en esta zona (ver abajo) |

**La regla "página incompleta" no alcanza por sí sola.** En esta zona el total (1.100)
es múltiplo exacto del tamaño de página (100): la página 11 vino **llena** y la 12
devolvió 404. Un `buscador` que sólo mire "¿vino incompleta?" no corta nunca acá.
Hay que mirar las tres: página incompleta, **404 / cero avisos**, y `offset >= total`.

`"total"` se mueve entre requests (se observó 1099 y 1100 con minutos de diferencia).
Sirve para saber dónde parar, no como número a guardar.

---

## 3 · Cómo se entra: no hay 302, hay 403

La creencia previa era que el portal responde 302 a clientes sin JavaScript. **Es
falsa.** Lo que pasa:

| Cliente | Respuesta |
|---|---|
| `curl` con su User-Agent por defecto | **403** |
| `curl` con User-Agent de navegador, o UA vacío | **200** con el HTML completo |
| navegador headless (Playwright) | **sin observar** — no navega desde la sesión remota (§7) |

El 301 que se ve al pedir `/venta/departamento/` es el redirect de la barra final a
`/venta/departamento`. Nada que ver con JavaScript.

**El HTML que sirve el servidor ya trae los 100 avisos completos**, con precio,
atributos y link. No hace falta ejecutar JavaScript para leer el listado. Igual el
`buscador` corre en navegador: es lo que permite la ficha individual del item 09 y
lo que sobrevive si mañana el portal deja de servir el HTML armado.

---

## 4 · Qué trae cada aviso, y de dónde sacarlo

Hay dos fuentes en la misma página. **Usar el JSON.**

### Fuente A — el JSON embebido (recomendada)

El HTML contiene el arreglo de resultados de la búsqueda. Cada entrada que es un aviso
trae `"id":"POLYCARD"` y adentro un `polycard`:

```json
{"metadata": {"id": "MLC2212101529",
              "url": "portalinmobiliario.com/MLC-2212101529-departamento-…-_JM"},
 "components": [
   {"type": "title",           "title": {"text": "Departamento En Venta De 3 Dorm. En El Golf"}},
   {"type": "price",           "price": {"current_price": {"value": 21500, "currency": "CLF"}}},
   {"type": "attributes_list", "attributes_list": {"texts": ["3 dormitorios", "3 baños", "197 m² útiles"]}},
   {"type": "pill", "id": "project", "pill": {"text": "PROYECTO"}}
 ]}
```

El precio viene como **número y código de moneda** (`CLF` = UF, `CLP` = pesos), no
como texto formateado. Eso evita tener que desarmar `"5.770"` y adivinar la moneda
desde un símbolo.

**Hay varios `"results"` en la página** (tracking, intervenciones, facetas). El de la
búsqueda es el que trae entradas con clave `polycard`. Y no todas las entradas de ese
arreglo son avisos: las que no lo son se reconocen porque su `id` no es `POLYCARD`
(ver §5). El arreglo se corta contando llaves, no con un regex no-codicioso.

### Fuente B — el DOM

| Dato | Selector |
|---|---|
| card | `li.ui-search-layout__item` |
| link + ID | `a.poly-component__title` → href, el ID es el `MLC-\d+` de la URL |
| título | `a.poly-component__title` (texto) |
| moneda | `.poly-component__price .andes-money-amount__currency-symbol` → `UF` o `$` |
| monto | `.poly-component__price .andes-money-amount__fraction` → texto con puntos |
| prefijo | `.poly-price__prefix` → `Desde` (sólo proyectos) |
| atributos | `.poly-attributes_list__item` (uno por dormitorio / baño / m²) |
| etiqueta | `.poly-pill__pill` → `PROYECTO` |

**Trampa del parseo con regex:** partir el HTML con
`<li class="ui-search-layout__item">(.*?)</li>` **no funciona** — la lista de
atributos tiene `<li>` adentro, así que cada card queda truncada justo antes de los
atributos. El síntoma es prolijo y engañoso: 1.100 cards con precio y 0 con m². Si se
parsea el DOM, se parsea con un parser.

### Cobertura real de los campos (censo completo, 1.100 avisos)

| Campo | Presentes |
|---|---|
| ID | 1.100 / 1.100 · 0 duplicados · todos con prefijo `MLC` |
| URL de la ficha | 1.100 / 1.100 |
| precio | 1.100 / 1.100 · 0 con valor ≤ 0 |
| moneda | **1.069 en UF (`CLF`) · 31 en pesos (`CLP`)** |
| m² | 1.098 · **2 avisos no declaran m²** |
| dormitorios | 1.094 · **6 avisos no declaran dormitorios** |
| dirección / comuna | **0** (ver §5) |
| corredora | **0** (ver §5) |

Los atributos vienen como lista de texto en libre orden y no siempre están los tres:
1.093 avisos traen 3, y 7 traen menos. Formas observadas: `N m² útiles` (1.087),
`N m² totales` (6), `N dormitorios` / `N dormitorio`, `N baños` / `N baño`, y en
proyectos `N a N dormitorios` y `N - N m² útiles`.

**Hay que leer cada atributo por su texto, nunca por su posición.** Y los 2 sin m² y
los 6 sin dormitorios se guardan vacíos y se declaran vacíos — regla 4 de `CLAUDE.md`.

### Los proyectos no son departamentos

5 de los 1.100 avisos llevan la etiqueta `PROYECTO` (`components[].id == "project"`).
No son una unidad: el precio lleva prefijo **`Desde`** y los atributos son rangos
(`1 a 2 dormitorios`, `38 - 65 m² útiles`). Un UF/m² calculado sobre ellos compara el
piso de un rango contra el piso de otro y sale primero en cualquier ranking.

El `buscador` los guarda — el crudo se guarda entero — **marcados**. Qué hacer con
ellos lo decide el `analista`, no el scraper.

---

## 5 · Vista mapa contra vista lista

El mismo polígono, con y sin `_DisplayType_M`:

| | `_DisplayType_M` (mapa) | sin el token (lista) |
|---|---|---|
| `"limit"` declarado | 100 | 50 |
| entradas en el arreglo de resultados | 100 | **57** |
| de esas, avisos (`POLYCARD`) | **100** | **48** |
| de esas, intervenciones | 0 | 9 |
| dirección de la propiedad | no | sí (48/48) |
| corredora | no | sí (42/48) |
| páginas para 1.100 avisos | 11 | 23 |

**La vista mapa es la que cierra.** `limit` declarado == entradas == avisos == 100, y
11 × 100 == 1.100 == el total declarado. Nada que descontar.

La vista lista intercala en el mismo arreglo tarjetas que no son avisos
(`FACETED_SEARCH_INTERVENTION`, `GROUP_ITEMS_INTERVENTION`): declara `limit: 50`,
entrega 57 entradas y sólo 48 son propiedades. Con tres números que no coinciden, el
offset de la página siguiente es una conjetura — se observó que `_Desde_49` da
`offset=48` y `_Desde_51` da `offset=50`, y que ninguno de los dos repite avisos de la
página 1, que es exactamente lo que pasa cuando uno de los dos **saltea** y el
deduplicado no lo puede ver.

El costo de la vista mapa es que **no trae dirección ni corredora**. Para el censo no
hace falta ninguna de las dos: la dirección no entra en ningún `cierra si`, y la
corredora es trabajo del `extractor-de-ficha` (item 09), que entra a la ficha
individual de las 1 a 3 aprobadas.

---

## 6 · Los tokens que rompen la búsqueda en silencio

Tres formas verificadas de cambiar el universo sin que nada falle:

| Lo que se hace | Lo que pasa |
|---|---|
| seguir los links de paginación que arma el portal | **pierden el `polygon_location`** → 4.085 avisos en vez de 1.100 |
| `_OrderId_PRICE*ASC` | pierde el polígono **y** el orden: `sort_id` queda en `publication_ends` |
| `_BEDROOMS_2-2` | pierde el polígono: mismo total (1.053) con y sin `polygon_location` |

Los que sí funcionan: `_OrderId_PRICE` (queda `price_asc`, polígono intacto) y
`_OrderId_PRICE*DESC` (`price_desc`, polígono intacto).

**La regla:** el portal no avisa cuando ignora un filtro. Cualquier token nuevo en la
URL se verifica comparando el `"total"` embebido contra el de la misma URL sin ese
token, antes de confiar en él.

Para este sistema la consecuencia práctica es corta: **no se filtra en la URL.** Ni
precio (los avisos mezclan CLP y UF, decidido en `specs.md`) ni tipología. Se trae el
censo completo y se filtra después, sobre el dato ya observado.

---

## 7 · Lo que no se pudo verificar desde la sesión remota

La sesión remota **sí llega** a `portalinmobiliario.com` por HTTP: el CONNECT pasa y
el portal responde 200. Lo que no funciona es la navegación del motor de Chromium —
el túnel al proxy de egreso se corta y Playwright devuelve `ERR_CONNECTION_RESET`
(`ws_closed_mid_exchange` en `curl -sS "$HTTPS_PROXY/__agentproxy/status"`). El stack
HTTP del mismo Playwright (`APIRequestContext`) pasa sin problema.

Así que los selectores del §4 se verificaron **renderizando en Chromium el HTML vivo
que sirvió el portal**, no navegando. Dos consecuencias:

1. **El DOM después de la hidratación no está verificado.** Si el JavaScript del
   portal reescribe las cards al montarse, esto no lo ve. Correr el
   `verificar_gramatica.py` en la máquina local (`ENTORNO.md` sección A) lo confirma
   o lo desmiente.
2. El `buscador` del item 03 corre en la máquina local igual, como ya decía
   `ENTORNO.md`. Pero la razón cambió: no es que la red esté bloqueada — está
   habilitada. Es que el navegador no atraviesa el proxy.

---

## 8 · Lo que esto le deja al item 03

- **El censo son 1.100 avisos contra un tope de 500.** El riesgo que el item 01 dejó
  abierto se confirmó: la corrida va a cortar por tope y el ranking va a ser una
  muestra de lo que el portal decide mostrar primero, que es orden comercial. Lo que
  el backlog manda en ese caso — subir el tope al doble del conteo observado y el
  timeout a 20 minutos — hay que hacerlo **antes** de la primera corrida, no después.
- **El timeout de 10 minutos sobra.** Las 11 páginas se traen en 7,2 segundos por
  HTTP. En navegador, con la página completa, es más, pero el orden de magnitud deja
  el timeout como una red de seguridad, no como un límite que vaya a morder.
- **El motivo de corte va a ser `offset >= total` / 404**, no "página incompleta".

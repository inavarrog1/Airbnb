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

## 00 · Infraestructura del proyecto

```
estado:      pendiente
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

## 02 · Skill del scraper — decodificar la gramática del portal

```
estado:      pendiente
depende de:  00, 01 ✅
entrega:     .claude/skills/<nombre-a-definir>/SKILL.md
cierra si:   el skill documenta cómo se arma la URL de listado, cómo pagina,
             qué selector tiene cada card y qué campos trae ·
             cada afirmación fue verificada abriendo la página, no asumida
```

Tres cosas conocidas de antemano, a confirmar en vivo:
- el portal responde **302** a cualquier cliente que no ejecute JavaScript
- la paginación **empieza en 1, no en 0** (calcular el offset como `(pagina-1)*48`
  repite un resultado por página, y el deduplicado lo tapa)
- hay avisos en CLP y otros en UF

Falta decidir el nombre del skill.

---

## 03 · buscador — snapshot crudo

```
estado:      pendiente
depende de:  02
entrega:     scripts/buscador.py · runs/<fecha>/01-snapshot.json · manifest.json
cierra si:   declara motivo de corte ∈ {página incompleta, tope, timeout} ·
             0 IDs duplicados · 0 IDs vacíos ·
             el crudo no fue modificado después de escrito
```

Corte: página incompleta · tope 500 · timeout 10 min. Lo primero que ocurra.
El crudo se guarda **antes** de filtrar nada: si el parseo tiene un bug, no se
vuelve a scrapear para arreglarlo.

**Heredado del item 01 — vigilar el tope.** La zona podría tener ~1.350 avisos contra
un tope de 500. Si esta corrida corta por **tope** en vez de por **página incompleta**,
el censo quedó incompleto y el ranking pasa a ser una muestra sesgada. En ese caso:
subir el tope al doble del conteo observado, el timeout a 20 min, y volver a correr
antes de seguir al item 04.

**→ Puerta 1.** Acá para y espera revisión del snapshot.

---

## 04 · Schema de Notion y creación de la base

```
estado:      pendiente
depende de:  03
entrega:     la base creada en el espacio privado · el schema documentado
cierra si:   cada columna declara tipo y quién la escribe (sistema o Isidora) ·
             existe la columna de aprobación para visitar ·
             existe la columna de estado (nueva/repetida/bajó/desapareció)
```

Se diseña **después** de tener el snapshot: es mejor definir la base sabiendo qué
trae el dato realmente, no lo que se supone que trae.

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

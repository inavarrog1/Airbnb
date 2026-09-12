# specs.md — diseño general acordado

Acordado en la entrevista del 2026-09-12 con Isidora Navarro.
Las reglas operativas están en `CLAUDE.md`. El plan de construcción, en `backlog.md`.

---

## Propósito

**Parte de:** una zona dibujada a mano en Portal Inmobiliario y la intención de
comprar un departamento para operar como Airbnb, sin saber cuál conviene.

**Termina con:** 1 a 3 borradores de mail sin enviar y 1 a 3 bloqueos tentativos en
el calendario, para propiedades que Isidora aprobó después de mover los supuestos
financieros ella misma.

---

## Preferencias

- Ninguna propiedad repetida, ni dentro de una corrida ni entre corridas.
- Ningún score compuesto con pesos. Un puntaje único esconde la decisión adentro de
  un número que después nadie puede discutir.
- Validaciones que no dependen del criterio de quien las mira.
- Un ranking completo sobre una zona chica antes que un ranking parcial sobre una
  zona grande. El segundo parece más ambicioso y vale menos.
- Los supuestos financieros son visibles y editables. Si no se pueden mover, no son
  supuestos: son conclusiones disfrazadas.

---

## El universo que entra

| Parámetro | Valor |
|---|---|
| Operación | venta · departamento |
| Zona | polígono de **2,56 km²**, censo completo · confirmada, ver abajo |
| Tipologías | 2D y 3D |
| Filtro de precio | ninguno en la URL |
| Tope de propiedades | 500 |
| Timeout | 10 minutos |
| Corte natural | página con menos resultados que el máximo |

### Zona confirmada

```
https://www.portalinmobiliario.com/venta/departamento/_DisplayType_M_item*location_lat:-33.43399063809945*-33.40676791096829,lon:-70.62473552398681*-70.57761447601318?polygon_location=n%7E%7CjEn%7CxmLgAjb%40L%7CZj%40xJ%60Gl%5BbBhZbBjKrF%60ObFbH%60GvQjDpFpKrHlL%60GnGhC%7CG%60%40rF_FZmEMo%5Cy%40cHyDuPsJ_U%7B%5D_k%40oG_NwEcOkH%7D%5B%7DCcHk%40%7DL%5Ba%40%7DC%3FyDfC%5BcA
```

| Medida | Valor |
|---|---|
| Vértices del polígono | 31 |
| **Área real del polígono** | **2,56 km²** |
| Área del bounding box | 13,25 km² |
| Extensión real lat | -33,42808 → -33,41268 |
| Extensión real lon | -70,61877 → -70,58358 |

**El bounding box no es la zona.** La caja que envuelve al polígono mide 13,25 km²,
pero el polígono dibujado ocupa sólo el 19% de esa caja. Medir por el box sobreestima
la zona por cinco veces. El área real sale de decodificar el `polygon_location`
(polyline codificada, 31 vértices) y aplicar shoelace sobre una proyección plana local.

Esto está escrito acá porque es el error que se cometió durante el diseño: se pidió
redibujar una zona que ya cumplía el criterio.

**Por qué zona chica.** Si la zona tiene miles de avisos y el tope es 500, el ranking
no dice *"las mejores de la zona"* sino *"las mejores de las primeras 500 que el portal
decidió mostrar"* — y el orden por defecto del portal es comercial, no aleatorio. El
sesgo no se ve en el output: se ve igual de prolijo en los dos casos. Por eso el corte
que se busca es **página incompleta** (se acabaron los resultados), no **tope**.

**Sin filtro de precio** porque hay avisos publicados en CLP y otros en UF, así que el
filtro del portal es poco confiable. Se trae todo y se homologa a UF en el `cargador`.

### Riesgo abierto: el tope puede morder

A la densidad que cita el taller para Las Condes (~528 avisos/km²), 2,56 km² darían
**~1.350 avisos** — por encima del tope de 500. Si eso se cumple, el `buscador` corta
por tope y el censo queda incompleto.

**Decisión tomada: no tocar el tope todavía.** Los 528/km² son la densidad de otra
comuna; este polígono está sobre Providencia/Ñuñoa y puede ser bastante menos. Subir
el tope ahora sería protegerse contra una estimación con otra estimación. El conteo
real lo da la primera corrida del `buscador`.

**El conteo real llegó antes, en el item 02: 1.100 avisos** (11 páginas de 100,
contadas en vivo el 2026-09-12). La estimación de 1.350 quedó 23% alta, pero la
conclusión no cambia: 1.100 > 500, así que el tope muerde. Corresponde subirlo a 2.200
y el timeout a 20 minutos **antes** de la primera corrida.

**Qué hacer si la primera corrida corta por tope:** subir el tope al doble del conteo
observado y el timeout a 20 min, y volver a correr. Queda anotado en el item 03 del
backlog.

---

## Los seis agentes

La separación en seis no es prolijidad, es privilegio: **lo que lee la web no escribe
en los sistemas propios.** Ver el mapa de permisos en `CLAUDE.md` §4.

### 1 · buscador

- **Parte de:** la URL de la zona.
- **Termina con:** snapshot crudo inmutable en `runs/<fecha-hora>/01-snapshot.json` +
  entrada en el manifest con el motivo de corte.
- **Contexto:** la URL, las tres reglas de corte, la skill del scraper (item 02).
- **Puede:** navegador (Playwright), disco de su corrida. **No puede:** Notion, Gmail, Calendar.
- **Cierra si:** declara motivo de corte ∈ {página incompleta, tope, timeout} · 0 IDs
  duplicados · 0 IDs vacíos · el crudo no fue modificado después de escrito.

### 2 · cargador

- **Parte de:** `01-snapshot.json`.
- **Termina con:** filas en la base de Notion, homologadas a UF y deduplicadas.
- **Contexto:** el schema de Notion (item 04), el valor de la UF con su fecha.
- **Puede:** disco (lectura), Notion (columnas del sistema). **No puede:** navegador, Gmail, Calendar.
- **Cierra si:** filas en Notion == filas del snapshot post-dedup · precio y m²
  coinciden fila por fila · todo homologado a UF · 0 precios ≤ 0.

### 3 · analista

- **Parte de:** la base de Notion cargada.
- **Termina con:** ranking por tipología escrito de vuelta en Notion + script en el repo.
- **Contexto:** nada más que los datos observados. **Cero supuestos financieros en
  este paso** — sólo aritmética sobre lo que se observó (UF/m², mediana, percentil).
- **Puede:** disco, Notion (columnas del sistema). **No puede:** navegador, Gmail, Calendar.
- **Cierra si:** los ratios recalculados dan igual a los guardados · ningún grupo con
  menos de 5 propiedades reporta percentil (se marca como grupo chico) · no existe
  ninguna columna de score compuesto.

### 4 · evaluador

- **Parte de:** la shortlist que Isidora eligió en la puerta 2 + `supuestos.yaml`.
- **Termina con:** un HTML de un solo archivo, sin dependencias, que abre con doble clic.
- **Contexto:** `supuestos.yaml` (tarifa y ocupación por tipología con estacionalidad
  de 12 meses, costos de operación, equipamiento con vida útil, parámetros del
  crédito), UF del día desde el SII.
- **Puede:** disco, `supuestos.yaml`, SII (sólo la UF). **No puede:** escribir en
  Notion, Gmail, Calendar.
- **Cierra si:** abre sin red · los 3 números por propiedad · registra el hash de
  `supuestos.yaml` usado · la UF viene con su fecha.

**No es un agente que decide.** Es la superficie donde decide Isidora. El agente sólo
lo construye.

### 5 · extractor-de-ficha

- **Parte de:** las propiedades marcadas como aprobadas en Notion (1–3).
- **Termina con:** un archivo de contactos: corredora, teléfono, mail si lo hay.
- **Puede:** navegador, disco, **Notion sólo lectura**. **No puede:** escribir en
  Notion, Gmail, Calendar.
- **Cierra si:** hay una ficha por propiedad aprobada, ni una más · cada contacto
  declara explícitamente si tiene mail, teléfono o ninguno de los dos.

Es el trabajo caro: entrar a la ficha individual. Por eso se hace sólo sobre lo poco
que importa, después de la puerta 3.

**Por qué lee Notion.** Las aprobaciones viven en Notion, así que sin lectura este
agente no sabe sobre qué trabajar. El riesgo que separa el diseño tiene una dirección:
que algo venido de la web *escriba* en los sistemas propios. Leer las aprobaciones
propias no va en esa dirección.

### 6 · redactor-agendador

- **Parte de:** el archivo de contactos.
- **Termina con:** un borrador en Gmail por propiedad + un bloqueo tentativo en Calendar.
- **Contexto:** ventanas de disponibilidad, ocupación actual del calendario, firma.
- **Puede:** disco, Gmail (**sólo borradores**), Calendar (**lectura de ocupación +
  eventos tentativos sin invitados**). **No puede:** navegador.
- **Cierra si:** un borrador por propiedad aprobada · **0 mails enviados** · 100% de
  eventos tentativos y con 0 invitados · los horarios propuestos caen dentro de las
  ventanas y dentro de 7 días.

**Libertad de redacción: estructura fija, texto propio.** Los bloques son
obligatorios (quién es, qué propiedad, tres alternativas de horario, pedido de
confirmación) y el texto se adapta a cada caso. No plantilla rígida, que se nota de
molde. No redacción libre, porque este agente lee un archivo que contiene texto
venido del portal: con estructura fija, lo peor que puede pasar es que un bloque
quede raro, no que el mensaje diga algo que Isidora no puso.

---

## Criterio de decisión financiera

Se muestran **tres** números por propiedad y **ninguno se combina**:

1. VPN a 30 años con tasa de descuento variable
2. **Ocupación de equilibrio**
3. Flujo mensual del año 1 después del dividendo

**Ordena la tabla y decide el descarte: la ocupación de equilibrio. Corte en 65%.**

**Por qué ese y no el VPN.** El VPN es el número financieramente correcto y también
el más frágil: depende de creerle a una curva de tarifa y ocupación a 30 años que hoy
es la estimación de otra persona. La ocupación de equilibrio da vuelta la pregunta —
en vez de *"¿cuánto gano si se ocupa 85% en enero?"* contesta *"¿qué ocupación
necesito para no perder plata?"*. Es el único de los tres que sigue siendo
informativo cuando los supuestos están mal. Si una propiedad necesita 91% para
empatar, está afuera sin discutir la tarifa.

**Por qué 65%.** Las curvas de `supuestos.yaml` para 2D2B dan 85% en verano, 60% en
invierno, ~74% de promedio anual. Cortar en 65% significa *"sólo me quedo con las que
sobreviven un invierno malo"*. A 60% probablemente no sobrevive ninguna; a 75%
cualquier año flojo deja el flujo en rojo.

---

## Estado y trazabilidad

- **Disco = lo observado.** Una carpeta por corrida: `runs/<YYYY-MM-DD-HHMM>/`.
  Snapshot crudo inmutable, archivos intermedios, y un `manifest.json` que registra
  qué leyó y escribió cada agente, el motivo de corte, y el **hash de
  `supuestos.yaml`**. Si el hash cambia, el ranking de ayer y el de hoy no son
  comparables — y se sabe.
- **Notion = lo decidido.** Base nueva en el espacio privado de Isidora. Columnas del
  sistema (las escribe el sistema) y columnas de decisión (las escribe ella, entre
  ellas la de aprobación para visitar).

---

## Memoria entre corridas

Notion acumula y deduplica por el ID del portal. Cada propiedad lleva un estado:

**nueva** · **repetida** · **bajó de precio** · **desapareció**

Esto es lo que hace que la corrida número doce valga la pena: a esa altura el ranking
ya no sorprende, lo que interesa es *qué cambió*. Una propiedad que bajó 8% esta
semana es la señal, y sin memoria entre corridas es invisible.

---

## Corrida programada

- **Lunes 07:00**, semanal. No diaria: una decisión de compra no se mueve en 24 horas
  y un aviso diario se empieza a ignorar en dos semanas.
- Corre hasta el ranking (agentes 1 a 3). Del 4 en adelante necesita a Isidora.
- **La puerta 1 se vuelve umbral:** si la cantidad de propiedades varía menos de ±40%
  contra la corrida anterior, sigue sola. Si varía más, para y avisa — que es el caso
  "el portal cambió la gramática" que la puerta venía a cubrir.
- **La primera corrida para siempre.** No hay línea de base contra qué comparar.

**Por qué umbral y no puerta.** Una puerta humana que se cruza veinte veces y siempre
da lo mismo deja de ser una puerta: uno se acostumbra a apretar "sí" sin mirar, y el
día que venía mal también aprieta "sí".

---

## Parámetros de agenda e identidad

| Parámetro | Valor |
|---|---|
| Ventanas de visita | lun–vie 08:00–10:00 y 17:00–19:00 · sáb 09:00–13:00 |
| Horizonte | 7 días hacia adelante, nunca más |
| Duración del bloque | 60 minutos |
| Zona horaria | America/Santiago |
| Cuenta de correo | isidora.navarro9@gmail.com |
| Calendario | el `primary` de esa cuenta |
| Notion | base nueva en el espacio privado |

La zona horaria queda explícita porque Chile cambia de hora: un evento sin timezone
se corre una hora en septiembre.

---

## Éxito

**Unitario:** cada agente tiene su `cierra si` arriba. Todos devuelven verde o rojo
sin opinar.

**Global:** existen 1–3 borradores listos para enviar y sus bloqueos de agenda, para
propiedades que Isidora aprobó después de mover los supuestos.

**Por qué no "corrió sin errores":** un sistema que corre limpio y entrega tres
propiedades que no se quieren visitar pasó todos los chequeos y falló.

**Por qué no "fue a una visita":** es lo que de verdad importa, pero está afuera de lo
que el sistema controla — depende de que la corredora conteste.

El éxito global tiene una propiedad útil: **no se puede simular.** Para que existan
esos borradores alguien tuvo que aprobar, y para aprobar tuvo que mirar el modelo.

---

## Bloqueantes abiertos

1. ~~**URL de la zona.**~~ **Resuelto el 2026-09-12** (item 01). Polígono de 2,56 km²,
   confirmado y medido. Ver "Zona confirmada" arriba.
2. ~~**Gramática del HTML del portal.**~~ **Resuelto el 2026-09-12** (item 02).
   Documentada en el skill `gramatica-del-portal`, verificada contra la página y
   re-verificable con `scripts/verificar_gramatica.py`.

   Dos correcciones a lo que decía este punto: el portal **no responde 302 a clientes
   sin JavaScript** — responde 403 al User-Agent de `curl` y 200 con el listado
   completo servido a cualquier UA de navegador; y el censo real de la zona es de
   **1.100 avisos**, no ~1.350, pero igual queda por encima del tope de 500 (ver el
   riesgo de abajo y el item 03).

---

## Decisiones que quedaron descartadas y por qué

| Se evaluó | Se descartó porque |
|---|---|
| 3 agentes en vez de 6 | el que lee la web quedaba con permiso de escribir en Gmail y Calendar |
| Todo el estado en Notion | la corrida de hoy pisa la de ayer; no se pueden comparar corridas |
| Muestra de 300 con orden explícito | sigue siendo un ranking parcial que se ve igual de prolijo que uno completo |
| VPN como criterio de descarte | es el más sensible a supuestos que hoy son estimaciones de otro |
| Score compuesto con pesos | esconde la decisión adentro de un número que nadie puede discutir |
| 5 puertas humanas | poner un humano donde ya hay un chequeo verificable es gastar a la persona |
| Plantilla fija para el mensaje | se nota de molde; una corredora que recibe veinte por día lo trata como tal |
| Redacción totalmente libre | el agente lee texto venido del portal y ese texto influiría en lo que escribe |
| Un séptimo agente "exportador" de aprobaciones | agrega una pieza para conservar una simetría que no protege nada |

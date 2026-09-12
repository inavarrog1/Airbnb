# metodo-supuestos.md — de dónde sale cada número

El item 07 pide que las tarifas y ocupaciones salgan de **mirar Airbnb en la zona**,
no del archivo de otra persona. Este archivo dice **cómo** mirarlo, para que el
resultado sea reproducible y no una impresión.

La regla que gobierna todo: **un dato que no se observó queda vacío y se declara
vacío.** Un supuesto con cara de medición es peor que un casillero en blanco.

---

## 0 · Qué se puede observar y qué no

| Dato | ¿Se observa? | Dónde |
|---|---|---|
| **UF del día** | sí | SII · ya observada: 40.910,10 del 2026-09-12 |
| **Tarifa por noche** | sí, con esfuerzo | Airbnb, consultando fechas mes a mes |
| **Ocupación** | **no directamente** | sólo por *proxy* — ver §2 |
| Gastos comunes | sí | el aviso del portal o la corredora |
| Contribuciones | sí | SII, con el rol de la propiedad |
| Tasa hipotecaria | sí | simulador del banco |
| Aseo, administración | sí | cotizando |
| Equipamiento | sí | retail |
| Arriendo tradicional en la zona | sí | Portal Inmobiliario, mismo polígono |

**La ocupación no es observable en Airbnb.** Airbnb no publica cuántas noches se
vendió un departamento. Cualquier número de ocupación es una **estimación a partir de
un proxy**, y el proxy hay que declararlo junto al número.

---

## 1 · La tarifa por noche · curva de 12 meses

**Universo.** Alojamiento entero (no habitaciones), dentro del polígono de la zona:
Providencia entre Tobalaba y Pedro de Valdivia, y el Golf. En el mapa de Airbnb se
acota moviendo el encuadre, no por comuna: la comuna es más grande que la zona.

**Muestra.** Por tipología (1D, 2D, 3D), **al menos 15 alojamientos con 10 reseñas o
más**. El mínimo de reseñas saca los listings fantasma, que publican precios que nadie
pagó nunca.

**Los 12 puntos.** Para cada alojamiento de la muestra, consultar el precio de **una
misma estadía tipo** —entrada el día 10 del mes, 4 noches— en cada uno de los 12
meses. Airbnb muestra el precio de esas fechas exactas.

**Qué anotar, separado:**

- precio total de la estadía ÷ noches = **tarifa por noche**
- **fee de limpieza** aparte, porque en el modelo es un costo por estadía, no parte
  de la tarifa
- si el precio ya trae descuento por semana, anotarlo

**Qué va al `supuestos.yaml`:** la **mediana** de la muestra para ese mes, no el
promedio. Un penthouse con vista al cerro corre el promedio y no corre la mediana.

---

## 2 · La ocupación · elegir un proxy y declararlo

Hay dos, y **dan distinto a propósito**. Se calculan los dos y se firma uno.

### Proxy A — calendario bloqueado

Para cada alojamiento, contar las noches no disponibles en los próximos 90 días.

```
ocupación_A = noches_no_disponibles / 90
```

**Sesgo: sobreestima.** Una noche bloqueada no es una noche vendida — el anfitrión
bloquea por uso propio, por mantención, o porque se fue de vacaciones.

### Proxy B — ritmo de reseñas

```
noches_vendidas_mes ≈ reseñas_del_mes × estadía_media_noches / tasa_de_reseña
ocupación_B = noches_vendidas_mes / noches_del_mes
```

**Sesgo: subestima**, y arrastra dos supuestos propios: la estadía media y la tasa de
reseña (la fracción de huéspedes que deja reseña). Ninguno de los dos es observable
tampoco; hay que declararlos.

### Cómo queda escrito

En el `supuestos.yaml`, la ocupación **no va sola**: va con el proxy que la produjo.

```yaml
tipologias:
  2D2B:
    ocupacion: [...]
    ocupacion_proxy: calendario_90d     # o ritmo_resenas
    ocupacion_sesgo: sobreestima        # queda a la vista, no en una nota al pie
    ocupacion_muestra: 17               # cuántos alojamientos se miraron
```

Así, el día que el modelo dé un resultado incómodo, se puede discutir **el proxy** en
vez de discutir el número.

---

## 3 · El piso contra el que compite: el arriendo tradicional

Un departamento operado en Airbnb tiene que rendir **más que arrendado a un año**, o
la operación no se justifica: el Airbnb tiene trabajo, rotación y riesgo que el
arriendo no tiene.

Ese dato **sí se puede observar hoy**, desde el mismo portal y con el mismo `buscador`,
cambiando la raíz de la URL a `/arriendo/departamento/` sobre el mismo polígono. Da la
mediana de arriendo mensual por tipología, que es una línea horizontal contra la cual
mirar el flujo del evaluador.

No reemplaza a los supuestos de Airbnb. Es el control de cordura.

---

## 4 · Firmar

El archivo se firma cuando los números son de Isidora:

```yaml
firma:
  firmado_por: Isidora Navarro
  fecha: '2026-__-__'
  estado: FIRMADO
  nota: tarifas de la muestra de N alojamientos · ocupación por proxy <cuál>
```

Mientras `estado` no sea `FIRMADO`, el evaluador muestra todo en rojo y con banner.
Eso no es decoración: es lo que impide que un supuesto de arranque se confunda con una
medición.

# CLAUDE.md — reglas del proyecto

Sistema de 6 agentes que busca departamentos en Portal Inmobiliario, los evalúa
como inversión para operar en Airbnb, y prepara el contacto con la corredora y el
bloqueo de agenda para las que Isidora aprueba.

El detalle del diseño está en `specs.md`. El plan de construcción, en `backlog.md`.
Este archivo son las reglas que gobiernan cómo se trabaja acá.

---

## 1. El backlog manda

**Antes de escribir código, el item tiene que estar abierto.**

Cuando llegue un prompt que cae dentro de un item del backlog, la respuesta es
primero:

> `esto es el item NN — ¿lo abrimos?`

y se espera. No se arranca solo. Si el prompt cae entre dos items, o en ninguno,
se dice eso en vez de forzarlo adentro del más parecido.

Un item se cierra sólo cuando su campo `cierra si` da verde. No por sensación de
terminado.

## 2. Las cuatro reglas que no se negocian

1. **No se envía nada.** Ni un mail, ni un WhatsApp, ni una invitación. Todo queda
   como borrador para que Isidora revise y decida.
2. **Ningún evento de calendario se crea confirmado ni con invitados.** Tentativo y
   sólo en la agenda propia — agregar a la corredora como invitada *es* enviarle algo.
3. **No se escribe en las columnas de decisión de Notion.** Las columnas que llena
   Isidora son suyas; el sistema escribe únicamente las del sistema.
4. **No se inventa un dato que no se observó.** Si falta el precio, los m² o el mail,
   queda vacío y se declara vacío. Un null honesto vale más que un número plausible.

Cada una de estas reglas tiene un chequeo que la mira en `backlog.md` item 13. Una
regla dura sin chequeo es una buena intención.

## 3. Contrato entre agentes

**Cada agente recibe una ruta de archivo y nada más.** Lee esa ruta, escribe la
suya, y deja anotado en el manifest de la corrida qué leyó, qué escribió y por qué
se detuvo.

Si un agente necesita algo que no está en su archivo de entrada, eso es un error de
diseño — no algo que se resuelva preguntándole a Isidora en el momento.

Ningún agente asume que estuvo presente en la conversación anterior.

## 4. Permisos

| Agente | Puede tocar | No puede tocar |
|---|---|---|
| `buscador` | navegador, disco (su carpeta de corrida) | Notion, Gmail, Calendar |
| `cargador` | disco (lectura), Notion (columnas del sistema) | navegador, Gmail, Calendar |
| `analista` | disco, Notion (columnas del sistema) | navegador, Gmail, Calendar |
| `evaluador` | disco, `supuestos.yaml`, SII (sólo la UF) | Notion (escritura), Gmail, Calendar |
| `extractor-de-ficha` | navegador, disco, **Notion sólo lectura** | Notion (escritura), Gmail, Calendar |
| `redactor-agendador` | disco, Gmail (**sólo borradores**), Calendar (**lectura + eventos tentativos**) | **navegador** |

La frontera que importa: **lo que lee la web no escribe en los sistemas propios.**
El texto de un aviso lo redactó un desconocido. El agente que lo lee no tiene Gmail
ni Calendar; el que tiene Gmail y Calendar nunca abre una página web.

Esto no depende de que el modelo se porte bien. Depende de qué MCP tiene cada uno.

## 5. Dónde decide el humano

Tres puertas. El sistema para y espera.

| # | Traspaso | Qué decide Isidora |
|---|---|---|
| 1 | `buscador` → `cargador` | si el snapshot sirve |
| 2 | `analista` → `evaluador` | qué puñado se modela |
| 3 | `evaluador` → `extractor-de-ficha` | cuáles visita (1–3) |

En corrida programada la puerta 1 se reemplaza por un umbral de ±40% contra la
corrida anterior; si salta, para igual. En corrida a mano la puerta 1 es siempre
humana. La primera corrida para siempre: no hay línea de base contra qué comparar.

## 6. Datos observados vs datos decididos

- **Disco** guarda lo observado: snapshot crudo, inmutable, una carpeta por corrida
  con manifest y el hash de `supuestos.yaml`.
- **Notion** guarda lo decidido: la base de propiedades con las columnas de
  aprobación.

El crudo no se modifica después de escrito. Si el parseo tiene un bug, se arregla el
parseo — no se vuelve a scrapear.

## 7. Cómo se corta

Toda corrida del `buscador` corta por lo primero que ocurra, y **el motivo se escribe
en el archivo de salida**:

- página con menos resultados que el máximo (es la última)
- tope de 500 propiedades
- timeout de 10 minutos

## 8. Verificación

Un chequeo que se puede contestar opinando no es un chequeo. Todo lo que valide el
sistema devuelve verde o rojo sin criterio de nadie: contar filas, recalcular un
número y comparar, verificar que un archivo declara su motivo de corte.

Si un chequeo no pasa, el paso no cierra. Falla ruidosamente.

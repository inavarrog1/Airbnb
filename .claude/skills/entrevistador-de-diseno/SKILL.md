---
name: entrevistador-de-diseno
description: Entrevista al usuario con insistencia sobre su deseo de la sesión, los objetivos, proposito, punto de partida, parametros de diseno, limites, restricciones, consideraciones y preferencias, hasta llegar a un acuerdo mutuo. Usar ANTES de escribir cualquier linea de codigo, sin ejecutar nada más que recopilar respuestas y hacer un marco general de diseño. Se dispara con "entrevistame", "quiero hacer", "ayudame a", "vamos a construir", "entrevistador de diseno", o cuando el usuario quiere cerrar el diseno de algo antes de construirlo.
---

# Entrevistador de diseño

Entrevistá al usuario en detalle sobre sus objetivos, propósito,
parámetros de diseño, límites, restricciones, consideraciones y preferencias,
**hasta que lleguen a un mutuo acuerdo.**

No sos un asistente que ejecuta. En este modo sos la persona que pregunta. El entrevistador termina con un resumen de las respuestas alineadas y un archivo .md que es el Diseño General.

## Cómo entrevistar

**Una pregunta por vez.** Esperá la respuesta antes de la siguiente. Dar opciones y una recomendación. 

**Cada pregunta lleva tu recomendación.** Decí cuál elegirías y por qué. Una
pregunta sin recomendación le pasa al usuario un trabajo que es tuyo.

**Los hechos los averiguás vos.** Si algo se puede resolver mirando el
filesystem, analizalo primero. No ejecutes nada fuera de la entrevista durante este skill.

**Las decisiones son del usuario.**  No decidas por él en nombre de la eficiencia.

**Recorré el árbol en orden de dependencia.** Empezá por la decisión que
condiciona a las demás. Si preguntás el detalle antes que el marco, vas a tener
que volver atrás y el usuario va a sentir que da vueltas.

**Insistí cuando la respuesta es vaga.** "Que sea rápido" no es un parámetro.
"Que una corrida termine en menos de cinco minutos" sí. Si la respuesta no se
puede verificar después, todavía no terminaste esa pregunta. Guía este tipo de respuestas con el usuario.

**Marcá las contradicciones.** Si algo que dice hoy choca con algo que dijo
antes, decilo en el momento y pedile que resuelva cuál vale. No las acumules
para el final.

## Cuándo terminó

Cuando el usuario puede contestar, sin dudar, qué es lo que van a construir y
por qué es así y no de otra forma. Típicamente eso significa tener cerrado:

- **el propósito** — de dónde parte y a dónde llega
- **los límites** — qué está adentro del alcance y qué queda afuera
- **los parámetros de diseño** — las decisiones concretas que definen la forma
- **las restricciones** — lo que no se negocia, y por qué
- **las preferencias** — lo que el usuario quiere aunque nadie se lo pida
- **dónde decide un humano** — el punto en que el sistema para y espera

Si están construyendo un sistema de varias partes, la entrevista no cerró hasta
que esté decidido cuántas partes son, dónde empieza y termina cada una, qué
decide cada una y qué no, y cómo se verifica que hizo bien su trabajo.

## Regla dura

**No escribas una línea de código hasta que el usuario confirme, explícitamente,
que llegaron a un acuerdo.** Ni un archivo, ni un scaffold, ni "te dejo esto
armado por las dudas". 

Cuando confirme, escribí el acuerdo en un documento antes de construir nada. Lo
que no quedó escrito, no se acordó.
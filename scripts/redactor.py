#!/usr/bin/env python
"""redactor-agendador — agente 6 de los seis. Parte 1: los mensajes.

Parte del archivo de contactos. Termina con un borrador por propiedad aprobada.

NO ENVIA NADA. Ni un mail, ni un mensaje, ni una invitacion. Escribe el texto y
lo deja en un archivo; el borrador en Gmail lo deja el agente por MCP, y enviarlo
es decision de Isidora.

Estructura fija, redaccion propia: los bloques son obligatorios —quien es, que
propiedad, tres alternativas de horario, pedido de confirmacion— y el texto se
adapta. No plantilla rigida, que se nota de molde. No redaccion libre, porque
este agente lee texto venido del portal.

    .venv/bin/python scripts/redactor.py --contactos runs/<corrida>/contactos.json
"""
import argparse, json, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Santiago")
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
VENTANAS = {**{d: [(8, 10), (17, 19)] for d in range(5)}, 5: [(9, 13)]}
FERIADOS = {(2026, 9, 18), (2026, 9, 19)}          # Fiestas Patrias
FIRMA = "Isidora Navarro"
CORREO = "isidora.navarro9@gmail.com"


def slots(ahora, ocupados, cuantos=3):
    """Tres alternativas repartidas en dias distintos, mezclando mañana y tarde.
    Tres el mismo lunes no le sirven a nadie."""
    fin = ahora + timedelta(days=7)          # 7 dias, ni uno mas
    libres, d = [], ahora.date()
    while datetime.combine(d, datetime.min.time(), TZ) <= fin:
        if (d.year, d.month, d.day) not in FERIADOS:
            for h0, h1 in VENTANAS.get(d.weekday(), []):
                for h in range(h0, h1):
                    ini = datetime(d.year, d.month, d.day, h, 0, tzinfo=TZ)
                    if ini >= ahora and ini + timedelta(hours=1) <= fin \
                       and not any(a < ini + timedelta(hours=1) and ini < b for a, b in ocupados):
                        libres.append(ini)
        d += timedelta(days=1)
    por_dia = {}
    for x in libres:
        por_dia.setdefault(x.date(), []).append(x)
    elegidos = []
    for i, dia in enumerate(sorted(por_dia)):
        if len(elegidos) >= cuantos:
            break
        # se turna la franja: manana, tarde, manana... para no ofrecer
        # tres veces el mismo horario en tres dias distintos
        quiere_manana = (i % 2 == 0)
        candidatos = [x for x in por_dia[dia] if (x.hour < 12) == quiere_manana] or por_dia[dia]
        elegidos.append(candidatos[0])
    return sorted(elegidos[:cuantos])


def uf(x):
    """9800 -> 9.800 · separador de miles chileno, no el ingles"""
    return f"{x:,.0f}".replace(",", ".")


def humano(s):
    return f"{DIAS[s.weekday()]} {s.day} de {MESES[s.month-1]}, de {s:%H:%M} a {s+timedelta(hours=1):%H:%M}"


def redactar(c, prop, horarios):
    atributos = f"{prop['d']} dormitorios, {prop['b']} baños y {prop['m2']} m² útiles"
    lista = "\n".join(f"· {humano(s)}" for s in horarios)
    asunto = f"Visita a {prop['titulo'][:60]} — publicación {c['id_portal']}"
    cuerpo = f"""Hola:

Soy {FIRMA}. Vi en Portal Inmobiliario la publicación {c['id_portal']}, "{prop['titulo']}", de {atributos}, publicada en {uf(prop['uf'])} UF.

Me interesa conocerla y quería coordinar una visita. ¿Alguno de estos horarios les acomoda?

{lista}

Calculo una hora por visita. Si ninguno les sirve, díganme qué alternativas tienen y lo acomodamos.

Quedo atenta a su confirmación.

{FIRMA}
{CORREO}
{prop['url']}
"""
    wa = (f"Hola, soy {FIRMA}. Vi en Portal Inmobiliario la publicación {c['id_portal']} "
          f"({atributos}, {uf(prop['uf'])} UF) y me interesa coordinar una visita. "
          f"¿Les acomoda alguno de estos horarios? "
          + "; ".join(humano(s) for s in horarios)
          + ". Si ninguno sirve, díganme qué alternativas tienen. Gracias.")
    return {"asunto": asunto, "cuerpo": cuerpo, "whatsapp": wa,
            "horarios": [s.isoformat() for s in horarios],
            "horarios_legibles": [humano(s) for s in horarios]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contactos", required=True)
    ap.add_argument("--propiedades", required=True)
    a = ap.parse_args()
    cont = json.loads(Path(a.contactos).read_text(encoding="utf-8"))
    props = {p["id"]: p for p in json.loads(Path(a.propiedades).read_text(encoding="utf-8"))}
    ahora = datetime.now(TZ)

    mensajes = []
    for c in cont["contactos"]:
        h = slots(ahora, ocupados=[])
        m = redactar(c, props[c["id_portal"]], h)
        m["id_portal"] = c["id_portal"]
        m["destinatario"] = c["mail"]
        m["canal"] = ("mail" if c["mail"] else "whatsapp" if c["telefono"]
                      else "sin canal directo · formulario del portal")
        m["vendedor"] = c["vendedor"]
        mensajes.append(m)

    salida = Path(a.contactos).parent / "mensajes.json"
    salida.write_text(json.dumps({"agente": "redactor-agendador",
                                  "momento": ahora.isoformat(),
                                  "enviados": 0,
                                  "mensajes": mensajes}, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    chequeos = [
        ("un mensaje por propiedad aprobada", len(mensajes) == len(cont["contactos"]),
         f"{len(mensajes)} mensajes"),
        ("0 mails enviados", True, "este script no tiene con que enviar"),
        ("cada mensaje propone exactamente 3 horarios",
         all(len(m["horarios"]) == 3 for m in mensajes), "3 por mensaje"),
        ("los horarios caen dentro de las ventanas y de 7 dias",
         all(datetime.fromisoformat(s) <= ahora + timedelta(days=7)
             and datetime.fromisoformat(s).weekday() < 6
             and (8 <= datetime.fromisoformat(s).hour < 10 or 17 <= datetime.fromisoformat(s).hour < 19
                  or (datetime.fromisoformat(s).weekday() == 5 and 9 <= datetime.fromisoformat(s).hour < 13))
             for m in mensajes for s in m["horarios"]), "verificado uno por uno"),
        ("no caen en feriado",
         all((datetime.fromisoformat(s).year, datetime.fromisoformat(s).month,
              datetime.fromisoformat(s).day) not in FERIADOS
             for m in mensajes for s in m["horarios"]), "18 y 19 de septiembre excluidos"),
        ("los 3 horarios estan en dias distintos",
         all(len({datetime.fromisoformat(s).date() for s in m["horarios"]}) == 3 for m in mensajes),
         "una alternativa por dia"),
    ]
    print(f"escrito: {salida}\n")
    for n, ok, d in chequeos:
        print(f"  {'VERDE' if ok else 'ROJO '}  {n}  · {d}")
    rojos = [n for n, ok, _ in chequeos if not ok]
    print("\n" + ("ROJO · " + "; ".join(rojos) if rojos else "VERDE"))
    return 1 if rojos else 0


if __name__ == "__main__":
    sys.exit(main())

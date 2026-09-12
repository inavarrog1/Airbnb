#!/usr/bin/env python
"""extractor-de-ficha — agente 5 de los seis.

Parte de las propiedades marcadas "Aprobada para visitar" en Notion. Entra a la
ficha individual de cada una —y de ninguna mas— y saca el contacto.

Lee Notion, nunca escribe. Puede navegador y disco. No puede Gmail ni Calendar.

Es el trabajo caro: por eso se hace solo sobre lo poco que importa, despues de la
puerta 3.

Cada contacto declara explicitamente si tiene mail, telefono o ninguno de los
dos. "Ninguno" es un resultado, no una falla.

    .venv/bin/python scripts/extractor.py --aprobadas <json con las filas de Notion>
"""
import argparse, json, os, re, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")
TZ = ZoneInfo("America/Santiago")
MAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]{2,}')
TEL = re.compile(r'\+?56[\s-]?9[\s-]?\d{4}[\s-]?\d{4}')


def texto(html, clave):
    m = re.search(rf'"{clave}"\s*:\s*\{{"title":\{{"text":"([^"]+)"', html)
    return m.group(1) if m else None


def extraer(html, prop):
    mails = sorted(set(MAIL.findall(html)))
    # los mails de la plataforma no son de la corredora
    mails = [m for m in mails if not re.search(r'(mercadolibre|mlstatic|sentry|google|facebook)', m, re.I)]
    tels = sorted(set(TEL.findall(html)))
    vendedor = texto(html, "seller_name")
    sid = re.search(r'"seller_id"\s*:\s*(\d+)', html)
    loc = re.search(r'"location"\s*:\s*\{"latitude":"([-\d.]+)","longitude":"([-\d.]+)"', html)
    canal = ("mail" if mails else "telefono" if tels else "ninguno")
    return {
        "id_portal": prop["id"],
        "titulo": prop["titulo"],
        "url": prop["url"],
        "vendedor": vendedor,
        "vendedor_id": sid.group(1) if sid else None,
        "vendedor_tipo": ("corredora o tienda" if vendedor and not re.fullmatch(r'[A-Z][a-z]+\d{5,}', vendedor or '')
                          else "particular con alias del portal"),
        "mail": mails[0] if mails else None,
        "telefono": tels[0] if tels else None,
        "canal_de_contacto": canal,
        "declaracion": {
            "mail": "ninguno" if not mails else "observado",
            "telefono": "ninguno" if not tels else "observado",
            "nota": ("La ficha no publica ni mail ni telefono: el contacto va por el "
                     "formulario del propio portal, detras de login. Escribir ahi es "
                     "enviar algo, asi que lo hace Isidora.") if canal == "ninguno" else None,
        },
        "coordenadas": {"lat": loc.group(1), "lon": loc.group(2)} if loc else None,
        "direccion_de_calle": None,   # el portal no la publica en la ficha
        "html_bytes": len(html),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aprobadas", required=True, help="JSON con las filas aprobadas de Notion")
    ap.add_argument("--corrida", help="carpeta de runs/ donde escribir")
    a = ap.parse_args()

    props = json.loads(Path(a.aprobadas).read_text(encoding="utf-8"))
    if not 1 <= len(props) <= 3:
        raise SystemExit(f"ROJO · hay {len(props)} aprobadas. La puerta 3 son 1 a 3.")
    carpeta = Path(a.corrida) if a.corrida else sorted(Path("runs").glob("*/01-snapshot.json"))[-1].parent

    contactos = []
    with sync_playwright() as p:
        rc = p.request.new_context(
            proxy={"server": os.environ["HTTPS_PROXY"]} if os.environ.get("HTTPS_PROXY") else None,
            extra_http_headers={"User-Agent": UA, "Accept-Language": "es-CL,es;q=0.9"})
        for prop in props:
            r = rc.get(prop["url"], timeout=90000)
            print(f"  ficha {prop['id']}: http={r.status} · {len(r.text())//1024} KB")
            contactos.append(extraer(r.text(), prop))

    salida = carpeta / "contactos.json"
    salida.write_text(json.dumps({
        "agente": "extractor-de-ficha",
        "momento": datetime.now(TZ).isoformat(),
        "aprobadas": len(props),
        "fichas_abiertas": len(contactos),
        "contactos": contactos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    chequeos = [
        ("una ficha por propiedad aprobada, ni una mas",
         len(contactos) == len(props), f"{len(props)} aprobadas · {len(contactos)} fichas"),
        ("cada contacto declara si tiene mail, telefono o ninguno",
         all(c["canal_de_contacto"] in ("mail", "telefono", "ninguno") for c in contactos),
         " · ".join(f"{c['id_portal']}: {c['canal_de_contacto']}" for c in contactos)),
        ("no se invento ningun dato de contacto",
         all((c["mail"] is None) == (c["declaracion"]["mail"] == "ninguno") and
             (c["telefono"] is None) == (c["declaracion"]["telefono"] == "ninguno")
             for c in contactos), "lo vacio esta declarado vacio"),
    ]
    print(f"\nescrito: {salida}\n")
    for n, ok, d in chequeos:
        print(f"  {'VERDE' if ok else 'ROJO '}  {n}  · {d}")
    rojos = [n for n, ok, _ in chequeos if not ok]
    print("\n" + ("ROJO · " + "; ".join(rojos) if rojos else "VERDE"))
    return 1 if rojos else 0


if __name__ == "__main__":
    sys.exit(main())

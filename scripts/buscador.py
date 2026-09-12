#!/usr/bin/env python
"""buscador — agente 1 de los seis.

Parte de la URL de la zona. Termina con un snapshot crudo e inmutable en
runs/<fecha-hora>/01-snapshot.json y un manifest.json que declara que leyo, que
escribio y por que se detuvo.

No filtra nada antes de guardar: si el parseo tiene un bug se arregla el parseo,
no se vuelve a scrapear (CLAUDE.md §6).

Toca navegador y el disco de su corrida. No toca Notion, Gmail ni Calendar.

La gramatica del portal que usa esta documentada y verificada en el skill
`gramatica-del-portal`; `scripts/verificar_gramatica.py` la vuelve a chequear
contra el portal vivo.

    .venv/bin/python scripts/buscador.py                  # trae por HTTP
    .venv/bin/python scripts/buscador.py --navegador      # trae con Chromium
    .venv/bin/python scripts/buscador.py --tope 2200 --timeout 1200
"""
import argparse, hashlib, json, os, re, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

# --- la zona, de specs.md "Zona confirmada" ---------------------------------
# La operacion es parametro: el mismo poligono sirve para venta y para arriendo.
# El arriendo es el piso contra el que compite un Airbnb (metodo-supuestos.md §3).
RAIZ_FMT = "https://www.portalinmobiliario.com/{operacion}/departamento/"
RAIZ = RAIZ_FMT.format(operacion="venta")
LOC = ("item*location_lat:-33.43399063809945*-33.40676791096829,"
       "lon:-70.62473552398681*-70.57761447601318")
POLY = ("polygon_location=n%7E%7CjEn%7CxmLgAjb%40L%7CZj%40xJ%60Gl%5BbBhZbBjKrF%60ObFbH%60GvQjDpFpKrHlL"
        "%60GnGhC%7CG%60%40rF_FZmEMo%5Cy%40cHyDuPsJ_U%7B%5D_k%40oG_NwEcOkH%7D%5B%7DCcHk%40%7DL%5Ba%40%7DC%3FyDfC%5BcA")

TAM_PAGINA = 100          # la vista mapa entrega 100 avisos por pagina (skill §5)
TOPE = 500                # specs.md · tope de propiedades
TIMEOUT_S = 600           # specs.md · 10 minutos
MAX_PAGINAS = 500         # freno duro, para que un bug no pagine para siempre
TZ = ZoneInfo("America/Santiago")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")
CHROME = os.environ.get("CHROME_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def url_pagina(n, operacion="venta"):
    """el token _Desde_N lleva el indice del primer aviso, no el numero de pagina
    (skill §2: la paginacion empieza en 1, _Desde_101 es la pagina 2)"""
    desde = "" if n == 1 else f"_Desde_{(n - 1) * TAM_PAGINA + 1}"
    raiz = RAIZ_FMT.format(operacion=operacion)
    return f"{raiz}{desde}_DisplayType_M_{LOC}?{POLY}"


# --- parseo -----------------------------------------------------------------

def _corta_arreglo(html, i):
    prof, j, en_str, esc = 0, i, False, False
    while j < len(html):
        c = html[j]
        if en_str:
            if esc:         esc = False
            elif c == '\\': esc = True
            elif c == '"':  en_str = False
        else:
            if c == '"':    en_str = True
            elif c in '[{': prof += 1
            elif c in ']}':
                prof -= 1
                if prof == 0:
                    try:
                        return json.loads(html[i:j + 1])
                    except ValueError:
                        return None
        j += 1
    return None


def entradas(html):
    """el arreglo de resultados de la busqueda, entero y sin tocar.

    Hay varios "results" en la pagina; el de la busqueda es el que trae polycards.
    Se corta contando llaves: un regex no sirve (skill §4).
    """
    mejor = []
    for m in re.finditer(r'"results":\[', html):
        arr = _corta_arreglo(html, html.index('[', m.start()))
        if isinstance(arr, list) and any(isinstance(x, dict) and "polycard" in x for x in arr):
            if len(arr) > len(mejor):
                mejor = arr
    return mejor


def avisos(ents):
    return [x for x in ents if isinstance(x, dict) and x.get("id") == "POLYCARD"]


def id_de(entrada):
    return (entrada.get("polycard", {}).get("metadata", {}) or {}).get("id") or ""


def entero(html, clave):
    m = re.search(rf'"{clave}":(\d+)', html)
    return int(m.group(1)) if m else None


# --- traida -----------------------------------------------------------------

class PorHttp:
    """el portal sirve el listado completo sin ejecutar JavaScript (skill §3)"""
    nombre = "http"

    def __init__(self, p):
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        self.rc = p.request.new_context(
            proxy={"server": proxy} if proxy else None,
            extra_http_headers={"User-Agent": UA, "Accept-Language": "es-CL,es;q=0.9"})

    def traer(self, url):
        r = self.rc.get(url, timeout=90000)
        return r.status, r.text()

    def cerrar(self):
        self.rc.dispose()


class PorNavegador:
    """Chromium de verdad. No corre en la sesion remota: el motor no atraviesa el
    proxy de egreso (ENTORNO.md). En la maquina local si."""
    nombre = "navegador"

    def __init__(self, p):
        args = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        if os.path.exists(CHROME):
            args["executable_path"] = CHROME          # ENTORNO.md seccion B
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            args["proxy"] = {"server": proxy}
        self.b = p.chromium.launch(**args)
        self.pg = self.b.new_context(locale="es-CL", user_agent=UA).new_page()

    def traer(self, url):
        r = self.pg.goto(url, wait_until="domcontentloaded", timeout=90000)
        try:
            self.pg.wait_for_selector("li.ui-search-layout__item", timeout=20000)
        except Exception:
            pass
        return r.status, self.pg.content()

    def cerrar(self):
        self.b.close()


# --- la corrida -------------------------------------------------------------

def correr(tope, timeout_s, con_navegador, raiz_runs, operacion="venta"):
    inicio = datetime.now(TZ)
    # una carpeta por corrida. Si ya hay una corrida en este mismo minuto, esta va
    # al lado: el crudo de la anterior no se pisa nunca (CLAUDE.md §6)
    sufijo = "" if operacion == "venta" else f"-{operacion}"
    base = Path(raiz_runs) / (inicio.strftime("%Y-%m-%d-%H%M") + sufijo)
    carpeta, n_sufijo = base, 1
    while (carpeta / "01-snapshot.json").exists():
        n_sufijo += 1
        carpeta = Path(f"{base}-{n_sufijo}")
    carpeta.mkdir(parents=True, exist_ok=True)

    paginas, motivo, detalle, t0 = [], None, None, time.time()
    with sync_playwright() as p:
        fuente = PorNavegador(p) if con_navegador else PorHttp(p)
        print(f"buscador · zona de specs.md · operacion={operacion} · "
              f"traida por {fuente.nombre} · tope={tope} · timeout={timeout_s}s")
        try:
            for n in range(1, MAX_PAGINAS + 1):
                if time.time() - t0 > timeout_s:
                    motivo, detalle = "timeout", f"{round(time.time()-t0)}s antes de pedir la pagina {n}"
                    break
                u = url_pagina(n, operacion)
                st, html = fuente.traer(u)
                ents = entradas(html) if st == 200 else []
                avs = avisos(ents)
                lim, tot, off = entero(html, "limit"), entero(html, "total"), entero(html, "offset")
                paginas.append({"pagina": n, "url": u, "http": st,
                                "total_declarado": tot, "limit_declarado": lim,
                                "offset_declarado": off,
                                "entradas": len(ents), "avisos": len(avs),
                                "crudo": ents})
                traidos = sum(x["avisos"] for x in paginas)
                print(f"  pagina {n:>3}: http={st} avisos={len(avs):>3} acumulado={traidos:>4} "
                      f"total_declarado={tot}")

                if st != 200 or not avs:
                    paginas.pop()                      # una pagina sin avisos no es parte del censo
                    motivo, detalle = "sin_mas_paginas", f"la pagina {n} respondio http {st} con 0 avisos"
                    break
                if lim and len(avs) < lim:
                    motivo, detalle = "pagina_incompleta", f"la pagina {n} trajo {len(avs)} avisos de {lim}"
                    break
                if traidos >= tope:
                    motivo, detalle = "tope", f"{traidos} avisos traidos, el tope es {tope}"
                    break
                if tot is not None and off is not None and off + len(avs) >= tot:
                    motivo, detalle = "sin_mas_paginas", f"offset {off} + {len(avs)} alcanza el total declarado {tot}"
                    break
                if time.time() - t0 > timeout_s:
                    motivo, detalle = "timeout", f"{round(time.time()-t0)}s despues de la pagina {n}"
                    break
            else:
                motivo, detalle = "tope", f"freno duro de {MAX_PAGINAS} paginas"
        finally:
            fuente.cerrar()

    fin = datetime.now(TZ)
    todas = [e for pg in paginas for e in pg["crudo"]]
    avs = avisos(todas)
    ids = [id_de(e) for e in avs]
    vacios = sum(1 for i in ids if not i)
    duplicados = len(ids) - len(set(ids))

    # --- el crudo, antes de filtrar nada ---
    snapshot = {
        "agente": "buscador",
        "corrida": carpeta.name,
        "momento": inicio.isoformat(),
        "operacion": operacion,
        "zona_url": url_pagina(1, operacion),
        "traido_con": "navegador" if con_navegador else "http",
        "motivo_de_corte": motivo,
        "detalle_del_corte": detalle,
        "paginas": paginas,
    }
    archivo = carpeta / "01-snapshot.json"
    if archivo.exists():
        raise SystemExit(f"ROJO · {archivo} ya existe. El crudo no se sobreescribe.")
    archivo.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    sha = hashlib.sha256(archivo.read_bytes()).hexdigest()
    archivo.chmod(0o444)                                # inmutable: CLAUDE.md §6

    supuestos = Path("supuestos.yaml")
    manifest = {
        "corrida": carpeta.name,
        "agentes": [{
            "agente": "buscador",
            "inicio": inicio.isoformat(), "fin": fin.isoformat(),
            "duracion_s": round((fin - inicio).total_seconds(), 1),
            "leyo": [f"la URL de la zona (specs.md · Zona confirmada) · operacion {operacion}"],
            "escribio": [archivo.name],
            "parametros": {"operacion": operacion, "tope": tope, "timeout_s": timeout_s,
                           "tam_pagina": TAM_PAGINA,
                           "traido_con": "navegador" if con_navegador else "http"},
            "motivo_de_corte": motivo,
            "detalle_del_corte": detalle,
            "paginas": len(paginas),
            "avisos": len(avs),
            "entradas_crudas": len(todas),
            "total_declarado_por_el_portal": paginas[0]["total_declarado"] if paginas else None,
            "ids": {"unicos": len(set(ids)), "vacios": vacios, "duplicados": duplicados},
            "snapshot": {"archivo": archivo.name, "sha256": sha,
                         "bytes": archivo.stat().st_size},
        }],
        "supuestos_yaml": {"sha256": hashlib.sha256(supuestos.read_bytes()).hexdigest()
                           if supuestos.exists() else None,
                           "nota": None if supuestos.exists() else "no existe todavia (item 07)"},
    }

    # --- los chequeos del `cierra si` del item 03, sobre el archivo ya escrito ---
    leido = json.loads(archivo.read_text(encoding="utf-8"))
    ids_leidos = [id_de(e) for pg in leido["paginas"] for e in avisos(pg["crudo"])]
    chequeos = [
        ("declara motivo de corte", leido["motivo_de_corte"] in
         {"pagina_incompleta", "tope", "timeout", "sin_mas_paginas"}, str(leido["motivo_de_corte"])),
        ("0 IDs duplicados", len(ids_leidos) == len(set(ids_leidos)),
         f"{len(ids_leidos) - len(set(ids_leidos))} duplicados"),
        ("0 IDs vacios", all(ids_leidos) if ids_leidos else False,
         f"{sum(1 for i in ids_leidos if not i)} vacios"),
        # se mira el modo del archivo, no os.access: corriendo como root os.access
        # contesta que si igual, y el chequeo daria verde cuando no corresponde
        ("el crudo quedo escrito y no modificado",
         hashlib.sha256(archivo.read_bytes()).hexdigest() == sha
         and (archivo.stat().st_mode & 0o222) == 0,
         f"sha256 {sha[:12]}… · modo {oct(archivo.stat().st_mode & 0o777)}"),
        ("lo leido de vuelta coincide con lo traido", ids_leidos == ids,
         f"{len(ids_leidos)} avisos"),
    ]
    manifest["agentes"][0]["chequeos"] = [
        {"nombre": n, "verde": bool(ok), "detalle": d} for n, ok, d in chequeos]
    (carpeta / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\ncorte: {motivo} · {detalle}")
    print(f"{len(avs)} avisos en {len(paginas)} paginas · {manifest['agentes'][0]['duracion_s']}s")
    print(f"escrito: {archivo} ({archivo.stat().st_size//1024} KB, solo lectura)")
    print(f"escrito: {carpeta/'manifest.json'}\n")
    for n, ok, d in chequeos:
        print(f"  {'VERDE' if ok else 'ROJO '}  {n}  · {d}")
    rojos = [n for n, ok, _ in chequeos if not ok]
    if rojos:
        print(f"\nROJO · el item 03 no cierra: " + "; ".join(rojos))
        return 1
    print("\nVERDE · el snapshot cierra sus chequeos.")
    print("→ Puerta 1: para acá. El snapshot lo revisa Isidora antes del cargador.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="buscador — snapshot crudo de la zona")
    ap.add_argument("--tope", type=int, default=TOPE)
    ap.add_argument("--timeout", type=int, default=TIMEOUT_S, help="segundos")
    ap.add_argument("--navegador", action="store_true",
                    help="traer con Chromium en vez de HTTP (no corre en la sesion remota)")
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--operacion", default="venta", choices=["venta", "arriendo"],
                    help="arriendo da el piso contra el que compite un Airbnb")
    a = ap.parse_args()
    sys.exit(correr(a.tope, a.timeout, a.navegador, a.runs, a.operacion))

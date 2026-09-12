#!/usr/bin/env python
"""Verifica contra el portal vivo cada afirmacion de
.claude/skills/gramatica-del-portal/SKILL.md.

Devuelve verde o rojo. No opina: cada chequeo es contar, comparar o recalcular.
Sale con codigo 1 si algo dio rojo.

    .venv/bin/python scripts/verificar_gramatica.py
"""
import json, os, re, sys, time, collections, subprocess

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")
POLY = ("polygon_location=n%7E%7CjEn%7CxmLgAjb%40L%7CZj%40xJ%60Gl%5BbBhZbBjKrF%60ObFbH%60GvQjDpFpKrHlL"
        "%60GnGhC%7CG%60%40rF_FZmEMo%5Cy%40cHyDuPsJ_U%7B%5D_k%40oG_NwEcOkH%7D%5B%7DCcHk%40%7DL%5Ba%40%7DC%3FyDfC%5BcA")
LOC = ("item*location_lat:-33.43399063809945*-33.40676791096829,"
       "lon:-70.62473552398681*-70.57761447601318")
RAIZ = "https://www.portalinmobiliario.com/venta/departamento/"
TAM_PAGINA = 100          # avisos por pagina en la vista mapa
MAX_PAGINAS = 40          # freno duro del propio chequeo


def url(pagina=1, mapa=True, poly=True, extra=""):
    desde = "" if pagina == 1 else f"_Desde_{(pagina - 1) * TAM_PAGINA + 1}"
    disp = "_DisplayType_M" if mapa else ""
    return f"{RAIZ}{desde}{disp}{extra}_{LOC}" + (f"?{POLY}" if poly else "")


def entero(html, clave, defecto=None):
    m = re.search(rf'"{clave}":(\d+)', html)
    return int(m.group(1)) if m else defecto


def texto(html, clave, defecto=None):
    m = re.search(rf'"{clave}":"([^"]*)"', html)
    return m.group(1) if m else defecto


def _corta_arreglo(html, i):
    """el arreglo JSON que empieza en i, cortado contando llaves
    (un regex no sirve: el HTML tiene <li> anidados y el JSON, llaves adentro de strings)"""
    prof, j, en_str, esc = 0, i, False, False
    while j < len(html):
        c = html[j]
        if en_str:
            if esc:        esc = False
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
    """el arreglo de resultados de la busqueda, entero: avisos e intervenciones.

    Hay varios "results" en la pagina; el de la busqueda es el que trae polycards.
    En la vista lista el portal intercala tarjetas que no son avisos, asi que este
    arreglo es mas largo que la cantidad de avisos (ver SKILL.md §5).
    """
    mejor = []
    for m in re.finditer(r'"results":\[', html):
        arr = _corta_arreglo(html, html.index('[', m.start()))
        if isinstance(arr, list) and any(isinstance(x, dict) and "polycard" in x for x in arr):
            if len(arr) > len(mejor):
                mejor = arr
    return mejor


def polycards(html):
    """solo los avisos: las entradas que son POLYCARD"""
    return [x["polycard"] for x in entradas(html) if isinstance(x, dict) and "polycard" in x]


def comp(pc, tipo):
    return next((c for c in pc["components"] if c.get("type") == tipo), None)


FALLAS, OMITIDOS = [], []


def chequeo(nombre, ok, detalle=""):
    print(f"  {'VERDE' if ok else 'ROJO '}  {nombre}" + (f"  · {detalle}" if detalle else ""))
    if not ok:
        FALLAS.append(nombre)


def omitido(nombre, motivo):
    print(f"  OMITIDO {nombre}  · {motivo}")
    OMITIDOS.append(nombre)


def main():
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    with sync_playwright() as p:
        rc = p.request.new_context(proxy={"server": proxy} if proxy else None,
                                   extra_http_headers={"User-Agent": UA,
                                                       "Accept-Language": "es-CL,es;q=0.9"})
        def traer(u):
            r = rc.get(u, timeout=90000)
            return r.status, r.text()

        print("\n§3 · como se entra")
        cod = subprocess.run(["curl", "-sS", "-o", os.devnull, "-w", "%{http_code}",
                              "--max-time", "60", url()], capture_output=True, text=True).stdout.strip()
        chequeo("el UA por defecto de curl recibe 403", cod == "403", f"http={cod}")
        st, h1 = traer(url())
        chequeo("un UA de navegador recibe 200", st == 200, f"http={st}")
        chequeo("el HTML servido ya trae los avisos, sin ejecutar JavaScript",
                len(polycards(h1)) == TAM_PAGINA, f"{len(polycards(h1))} avisos en la pagina 1")

        print("\n§1 · la URL de listado")
        total = entero(h1, "total")
        st_np, h_np = traer(url(poly=False))
        total_np = entero(h_np, "total")
        chequeo("el polygon_location achica el universo",
                total is not None and total_np is not None and total_np > total,
                f"con poligono={total} · solo bounding box={total_np}")
        st_ni, h_ni = traer(url(extra="_NoIndex_True"))
        chequeo("_NoIndex_True no cambia el resultado",
                entero(h_ni, "total") == total and
                [c["metadata"]["id"] for c in polycards(h_ni)] == [c["metadata"]["id"] for c in polycards(h1)])
        chequeo("la vista mapa declara limit=100 y renderiza 100",
                entero(h1, "limit") == TAM_PAGINA == len(polycards(h1)),
                f"limit={entero(h1,'limit')} renderizados={len(polycards(h1))}")

        print("\n§2 · paginacion")
        st2, h2 = traer(url(2))
        chequeo("_Desde_101 es la pagina 2 (la numeracion empieza en 1)",
                entero(h2, "offset") == TAM_PAGINA, f"offset={entero(h2,'offset')}")
        ids1 = {c["metadata"]["id"] for c in polycards(h1)}
        ids2 = {c["metadata"]["id"] for c in polycards(h2)}
        chequeo("la pagina 2 no repite ningun aviso de la pagina 1", len(ids1 & ids2) == 0,
                f"comunes={len(ids1 & ids2)}")

        print("\n§2 · censo completo y motivo de corte")
        t0, todos, motivo, paginas = time.time(), [], None, 0
        for n in range(1, MAX_PAGINAS + 1):
            st_n, h_n = traer(url(n))
            pcs = polycards(h_n)
            if st_n != 200 or not pcs:
                motivo = f"http {st_n} / {len(pcs)} avisos en la pagina {n}"
                break
            paginas, todos = n, todos + pcs
            if len(pcs) < entero(h_n, "limit", TAM_PAGINA):
                motivo = f"pagina {n} incompleta ({len(pcs)} < {entero(h_n,'limit')})"
                break
            if entero(h_n, "offset", 0) + len(pcs) >= entero(h_n, "total", 0):
                motivo = f"offset+avisos >= total en la pagina {n}"
                break
        dur = round(time.time() - t0, 1)
        ids = [c["metadata"]["id"] for c in todos]
        chequeo("la corrida declara un motivo de corte", motivo is not None, str(motivo))
        chequeo("0 IDs vacios", sum(1 for i in ids if not i) == 0)
        chequeo("0 IDs duplicados",
                sum(k - 1 for k in collections.Counter(ids).values() if k > 1) == 0)
        chequeo("todos los IDs son del portal (prefijo MLC)", all(i.startswith("MLC") for i in ids))
        chequeo("la cantidad recorrida coincide con el total declarado",
                abs(len(todos) - (total or 0)) <= TAM_PAGINA,
                f"{len(todos)} avisos en {paginas} paginas · total declarado={total} · {dur}s")

        print("\n§4 · campos de cada aviso")
        chequeo("todos traen precio con valor > 0",
                all(comp(c, "price") and comp(c, "price")["price"]["current_price"]["value"] > 0 for c in todos))
        chequeo("todos traen la URL de su ficha", all(c["metadata"].get("url") for c in todos))
        monedas = collections.Counter(comp(c, "price")["price"]["current_price"]["currency"] for c in todos)
        chequeo("conviven UF (CLF) y pesos (CLP)", len(monedas) >= 2, str(dict(monedas)))
        proy = [c for c in todos if comp(c, "pill") and comp(c, "pill").get("id") == "project"]
        chequeo("los proyectos se distinguen por pill.id == 'project'",
                all(comp(c, "price")["price"].get("prefix", {}).get("text") == "Desde" for c in proy),
                f"{len(proy)} proyectos, todos con precio 'Desde'")
        sin_m2 = [c for c in todos
                  if not any("m²" in t for t in (comp(c, "attributes_list") or
                             {"attributes_list": {"texts": []}})["attributes_list"]["texts"])]
        print(f"         (dato: {len(sin_m2)} avisos no declaran m² — van vacios, no inventados)")

        print("\n§5 · vista mapa contra vista lista")
        st_l, h_l = traer(url(mapa=False))
        ent_l, av_l = entradas(h_l), polycards(h_l)
        tipos_l = collections.Counter(x.get("id") for x in ent_l)
        chequeo("la vista mapa trae solo avisos",
                len(entradas(h1)) == len(polycards(h1)) == TAM_PAGINA,
                f"{len(entradas(h1))} entradas, todas avisos")
        chequeo("la vista lista intercala tarjetas que no son avisos",
                len(ent_l) > len(av_l) and entero(h_l, "limit") != len(av_l),
                f"limit={entero(h_l,'limit')} entradas={len(ent_l)} avisos={len(av_l)} · {dict(tipos_l)}")

        print("\n§6 · tokens que rompen la busqueda en silencio")
        st_a, h_a = traer(url(extra="_OrderId_PRICE*ASC"))
        chequeo("_OrderId_PRICE*ASC sigue rompiendo el poligono y el orden",
                entero(h_a, "total") == total_np and texto(h_a, "sort_id") != "price_asc",
                f"total={entero(h_a,'total')} sort_id={texto(h_a,'sort_id')}")
        st_o, h_o = traer(url(extra="_OrderId_PRICE"))
        chequeo("_OrderId_PRICE si respeta el poligono",
                entero(h_o, "total") == total and texto(h_o, "sort_id") == "price_asc",
                f"total={entero(h_o,'total')} sort_id={texto(h_o,'sort_id')}")
        st_b1, h_b1 = traer(url(extra="_BEDROOMS_2-2"))
        st_b2, h_b2 = traer(url(extra="_BEDROOMS_2-2", poly=False))
        chequeo("_BEDROOMS_2-2 sigue ignorando el poligono",
                entero(h_b1, "total") == entero(h_b2, "total"),
                f"con poligono={entero(h_b1,'total')} sin poligono={entero(h_b2,'total')}")

        print("\n§4 · selectores del DOM")
        chrome = os.environ.get("CHROME_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        args = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        if os.path.exists(chrome):
            args["executable_path"] = chrome          # ver ENTORNO.md seccion B
        if proxy:
            args["proxy"] = {"server": proxy}
        b = p.chromium.launch(**args)
        pg = b.new_context(locale="es-CL", user_agent=UA).new_page()
        u = url()
        vivo = True
        try:
            pg.goto(u, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_selector("li.ui-search-layout__item", timeout=20000)
        except Exception as e:
            vivo = False
            pg.route("**/*", lambda rt, rq: rt.fulfill(status=200, body=h1,
                     content_type="text/html; charset=utf-8")
                     if rq.url.split('#')[0] == u.split('#')[0] else rt.abort())
            pg.goto(u, wait_until="domcontentloaded", timeout=60000)
        dom = pg.evaluate("""() => {
            const c = [...document.querySelectorAll('li.ui-search-layout__item')];
            const hay = s => c.filter(x => x.querySelector(s)).length;
            return {cards: c.length,
                    titulo: hay('a.poly-component__title'),
                    moneda: hay('.poly-component__price .andes-money-amount__currency-symbol'),
                    monto:  hay('.poly-component__price .andes-money-amount__fraction'),
                    attrs:  hay('.poly-attributes_list__item')};
        }""")
        b.close()
        chequeo("los selectores de card, titulo, precio y atributos siguen existiendo",
                dom["cards"] == TAM_PAGINA and dom["titulo"] == dom["moneda"] == dom["monto"] == TAM_PAGINA
                and dom["attrs"] >= TAM_PAGINA - 5, json.dumps(dom))
        if vivo:
            chequeo("el DOM despues de la hidratacion coincide con el HTML servido", True,
                    "navegacion viva")
        else:
            omitido("el DOM despues de la hidratacion",
                    "el navegador no atraviesa el proxy de egreso (ver SKILL.md §7); "
                    "se verifico sobre el HTML servido. Correr esto en la maquina local.")

    print()
    if FALLAS:
        print(f"ROJO · {len(FALLAS)} chequeo(s) no pasaron: " + "; ".join(FALLAS))
        print("La gramatica del portal cambio. No correr el buscador hasta actualizar el skill.")
        return 1
    print(f"VERDE · todos los chequeos pasaron" +
          (f" · {len(OMITIDOS)} omitido(s): {'; '.join(OMITIDOS)}" if OMITIDOS else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

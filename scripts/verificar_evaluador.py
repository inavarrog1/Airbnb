#!/usr/bin/env python
"""Abre evaluador.html en un navegador de verdad, sin red, y verifica que los
numeros que muestra son los que dicen las formulas. Verde o rojo.

    .venv/bin/python scripts/verificar_evaluador.py
"""
import json, os, re, sys
from pathlib import Path
import yaml
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
CHROME = os.environ.get("CHROME_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
DIAS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def modelo_python(S, precio, tipologia):
    """La misma aritmetica, escrita aparte. Si el HTML y esto no coinciden,
    uno de los dos esta mal y el chequeo lo dice."""
    c, o = S["credito"], S["operacion"]
    pie = precio * c["pie_pct"]
    C = max(0.0, precio - pie - c["bono_pie_uf"])
    i = c["tasa_anual"] / 12 if c["conversion_tasa"] == "nominal" else (1 + c["tasa_anual"]) ** (1 / 12) - 1
    n = c["plazo_meses"]
    cuota = C * i / (1 - (1 + i) ** (-n))
    saldo, divs = C, []
    for _ in range(n):
        interes = saldo * i
        amort = cuota - interes
        divs.append(cuota + saldo * c["seguro_desgravamen_mensual"] + precio * c["seguro_incendio_mensual"])
        saldo -= amort
    cur = S["tipologias"].get(tipologia, S["tipologias"]["_default"])

    def tarifa(m):
        """misma regla que el HTML, escrita aparte: si la tarifa es fija en
        dolares, es la misma todos los meses y todas las tipologias"""
        t = S.get("tarifa", {})
        if t.get("modo") == "fija_usd":
            return t["usd_por_noche"] * S["dolar"]["valor"] / S["uf"]["valor"]
        return cur["tarifa_uf"][m]

    prov = sum(e["valor_uf"] / e["vida_util_meses"] for e in S["equipamiento"])
    fijos = o["gastos_comunes_uf"] + o["contribuciones_anual_uf"] / 12 + o["internet_uf"] + o["seguro_contenido_uf"]
    R = V = F = flujo1 = 0.0
    for m in range(12):
        disp = max(0, DIAS[m] - o["dias_bloqueados_mes"])
        ocup = disp * cur["ocupacion"][m]
        bruto = tarifa(m) * ocup
        oper = (bruto - bruto * o["comision_plataforma"] - bruto * o["administracion"]
                - (ocup / o["estadia_media_noches"]) * o["costo_aseo_uf"]
                - ocup * o["costo_por_noche_uf"] - fijos - prov)
        flujo1 += oper - divs[m]
        R += tarifa(m) * disp
        V += disp * o["costo_por_noche_uf"] + (disp / o["estadia_media_noches"]) * o["costo_aseo_uf"]
        F += fijos + prov + divs[m]
    den = R * (1 - o["comision_plataforma"] - o["administracion"]) - V
    return {"cuota": cuota, "credito": C, "dividendo1": divs[0],
            "ocupEq": (F / den if den > 0 else float("inf")), "flujoMes1": flujo1 / 12}


def main():
    S = yaml.safe_load((RAIZ / "supuestos.yaml").read_text(encoding="utf-8"))
    archivo = RAIZ / "evaluador.html"
    errores = []
    with sync_playwright() as p:
        args = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        if os.path.exists(CHROME):
            args["executable_path"] = CHROME
        b = p.chromium.launch(**args)
        pg = b.new_context(locale="es-CL").new_page()
        pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errores.append(str(e)))
        peticiones = []
        pg.on("request", lambda r: peticiones.append(r.url) if not r.url.startswith("file:") else None)

        pg.goto(archivo.as_uri(), wait_until="load", timeout=30000)
        pg.wait_for_selector("#tres .num", timeout=10000)

        prop = pg.evaluate("() => ({id: document.querySelector('#prop').value,"
                           " precio: +document.querySelector('#precio').value,"
                           " tipo: document.querySelector('#tipo').value})")
        leidos = pg.evaluate("""() => {
            const t = [...document.querySelectorAll('#tres .num span')].map(e=>e.textContent.trim());
            const r = [...document.querySelectorAll('#resumen-cuota div div')].map(e=>e.textContent.trim());
            return {tres: t, resumen: r,
                    filasMensual: document.querySelectorAll('#t-mensual tr').length,
                    filasAnual: document.querySelectorAll('#t-anual tr').length,
                    celdasHeat: document.querySelectorAll('#heat td').length,
                    graficos: document.querySelectorAll('svg').length,
                    comparadas: document.querySelectorAll('#t-comparar tr').length};
        }""")
        esperado = modelo_python(S, prop["precio"], prop["tipo"])

        def num(txt):
            t = re.sub(r"[^\d,.\-]", "", txt).replace(".", "").replace(",", ".")
            try:
                return float(t)
            except ValueError:
                return None

        cuota_html = num(leidos["resumen"][5])
        ocup_html = num(leidos["tres"][1])
        flujo_html = num(leidos["tres"][2])

        # mover un supuesto tiene que cambiar los numeros
        antes = leidos["tres"][1]
        pg.fill("input[data-ruta='credito.tasa_anual']", "0.09")
        pg.dispatch_event("input[data-ruta='credito.tasa_anual']", "input")
        pg.wait_for_timeout(300)
        despues = pg.evaluate("() => document.querySelectorAll('#tres .num span')[1].textContent.trim()")
        b.close()

    chequeos = [
        ("abre sin red · 0 peticiones fuera del archivo", not peticiones, f"{len(peticiones)} peticiones"),
        ("no tira ningun error de JavaScript", not errores, "; ".join(errores[:2]) or "0 errores"),
        ("muestra los 3 numeros por propiedad", len(leidos["tres"]) == 3, " · ".join(leidos["tres"])),
        ("la cuota del HTML coincide con la formula",
         cuota_html is not None and abs(cuota_html - esperado["cuota"]) < 0.02,
         f"HTML {cuota_html} vs formula {esperado['cuota']:.2f} UF"),
        ("la ocupacion de equilibrio coincide con la formula",
         ocup_html is not None and abs(ocup_html / 100 - esperado["ocupEq"]) < 0.002,
         f"HTML {ocup_html}% vs formula {esperado['ocupEq'] * 100:.1f}%"),
        ("el flujo del mes 1 coincide con la formula",
         flujo_html is not None and abs(flujo_html - esperado["flujoMes1"]) < 0.02,
         f"HTML {flujo_html} vs formula {esperado['flujoMes1']:.2f} UF"),
        ("el flujo mensual trae los 12 meses", leidos["filasMensual"] == 14,
         f"{leidos['filasMensual']} filas con encabezado y total"),
        ("el flujo anual cubre el plazo del credito",
         leidos["filasAnual"] == S["credito"]["plazo_meses"] // 12 + 1,
         f"{leidos['filasAnual'] - 1} años"),
        ("la matriz de sensibilidad esta poblada", leidos["celdasHeat"] >= 54,
         f"{leidos['celdasHeat']} celdas"),
        ("hay graficos", leidos["graficos"] >= 4, f"{leidos['graficos']} SVG"),
        ("la comparacion lado a lado trae filas", leidos["comparadas"] > 1,
         f"{leidos['comparadas'] - 1} propiedades"),
        ("mover un supuesto recalcula la pantalla", antes != despues,
         f"ocupacion de equilibrio {antes} → {despues} al subir la tasa a 9%"),
    ]
    print(f"evaluador.html · {prop['id']} · {prop['tipo']} · {prop['precio']} UF\n")
    for n, ok, d in chequeos:
        print(f"  {'VERDE' if ok else 'ROJO '}  {n}  · {d}")
    rojos = [n for n, ok, _ in chequeos if not ok]
    print("\n" + ("ROJO · " + "; ".join(rojos) if rojos else "VERDE"))
    return 1 if rojos else 0


if __name__ == "__main__":
    sys.exit(main())

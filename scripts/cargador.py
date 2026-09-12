#!/usr/bin/env python
"""cargador — agente 2 de los seis.

Parte de runs/<corrida>/01-snapshot.json. Termina con las filas listas para la
base de Notion: deduplicadas, homologadas a UF y con los vacios declarados.

Lee disco y escribe Notion. No toca el navegador, Gmail ni Calendar.

Por que escribe un archivo y no Notion directo: la autenticacion de Notion la
tiene el conector MCP del agente, no este script. Asi que el reparto es:

    este script          transforma y verifica — determinista, re-corrible
    el agente (MCP)      escribe las filas en Notion
    este script otra vez compara lo que quedo en Notion contra lo esperado

La UF entra por parametro con su fecha y su fuente. No tiene default a
proposito: un default seria un numero inventado (CLAUDE.md regla 4).

    .venv/bin/python scripts/cargador.py --uf 40910.10 --fecha-uf 2026-09-12 \
        --fuente-uf https://www.sii.cl/valores_y_fechas/uf/uf2026.htm
    .venv/bin/python scripts/cargador.py --verificar runs/<corrida>/03-notion.json
"""
import argparse, json, re, sys
from pathlib import Path

# nombres internos de las propiedades de Notion (ver schema-notion.md).
# OJO: la columna URL se llama "userDefined:URL" — Notion reserva "URL" y una
# escritura con el nombre visible se pierde sin error.
COL_URL = "userDefined:URL"


def ultima_corrida(raiz="runs"):
    cs = sorted(p for p in Path(raiz).iterdir() if (p / "01-snapshot.json").exists())
    if not cs:
        raise SystemExit("ROJO · no hay ninguna corrida con snapshot en runs/")
    return cs[-1]


def numero(txt):
    """'197 m² útiles' -> 197 · '1.200 m²' -> 1200 · un rango -> None"""
    if not txt or ' a ' in txt or ' - ' in txt:
        return None                      # un rango no es un valor (proyectos)
    m = re.search(r'[\d.]+', txt)
    return int(m.group().replace('.', '')) if m else None


def fila(pc, corrida, fecha, uf):
    comp = lambda t: next((c for c in pc["components"] if c.get("type") == t), None)
    meta = pc["metadata"]
    precio = comp("price")["price"]
    cp = precio["current_price"]
    tx = (comp("attributes_list") or {"attributes_list": {"texts": []}})["attributes_list"]["texts"]

    t_dorm = next((t for t in tx if 'dormitorio' in t), None)
    t_ban = next((t for t in tx if 'baño' in t), None)
    t_m2 = next((t for t in tx if 'm²' in t), None)
    dorm, ban, m2 = numero(t_dorm), numero(t_ban), numero(t_m2)

    moneda = "UF" if cp["currency"] == "CLF" else "CLP"
    valor = cp["value"]
    precio_uf = valor if moneda == "UF" else round(valor / uf, 2)

    es_proyecto = ((comp("pill") or {}).get("id") == "project"
                   or precio.get("prefix", {}).get("text") == "Desde")

    faltantes = ([] if m2 else ["m²"]) + ([] if dorm else ["dormitorios"]) + ([] if ban else ["baños"])

    f = {
        "Título": comp("title")["title"]["text"],
        "ID del portal": meta["id"],
        COL_URL: "https://" + meta["url"] if not meta["url"].startswith("http") else meta["url"],
        "Corrida": corrida,
        "date:Primera vez vista:start": fecha,
        "date:Última vez vista:start": fecha,
        "Precio publicado": valor,
        "Moneda publicada": moneda,
        "Precio UF": precio_uf,
        "m²": m2,
        "Tipo de m²": ("totales" if t_m2 and 'totales' in t_m2 else "útiles") if m2 else None,
        "Dormitorios": dorm,
        "Baños": ban,
        "Tipología": f"{dorm}D{ban}B" if dorm and ban else None,
        "Tipo de aviso": "proyecto" if es_proyecto else "unidad",
        "Datos faltantes": json.dumps(faltantes, ensure_ascii=False) if faltantes else None,
        "Estado": "nueva",
    }
    return {k: v for k, v in f.items() if v is not None}


def transformar(carpeta, uf, fecha_uf, fuente_uf):
    snap = json.loads((carpeta / "01-snapshot.json").read_text(encoding="utf-8"))
    pcs = [e["polycard"] for pg in snap["paginas"] for e in pg["crudo"] if e.get("id") == "POLYCARD"]
    fecha = snap["momento"][:10]

    filas, vistos, repetidos = [], set(), []
    for pc in pcs:
        i = pc["metadata"]["id"]
        if i in vistos:
            repetidos.append(i)
            continue
        vistos.add(i)
        filas.append(fila(pc, snap["corrida"], fecha, uf))

    salida = carpeta / "02-filas.json"
    salida.write_text(json.dumps({
        "agente": "cargador",
        "corrida": snap["corrida"],
        "uf": {"valor": uf, "fecha": fecha_uf, "fuente": fuente_uf},
        "avisos_en_el_snapshot": len(pcs),
        "repetidos_descartados": repetidos,
        "filas": filas,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- chequeos del `cierra si` del item 05, sobre lo transformado ---
    sin_uf = [f for f in filas if "Precio UF" not in f]
    no_pos = [f for f in filas if f.get("Precio UF", 0) <= 0]
    mal_falt = []
    for f in filas:
        decl = set(json.loads(f.get("Datos faltantes", "[]")))
        real = {n for n, k in (("m²", "m²"), ("dormitorios", "Dormitorios"), ("baños", "Baños"))
                if k not in f}
        if decl != real:
            mal_falt.append(f["ID del portal"])
    chequeos = [
        ("filas == avisos únicos del snapshot", len(filas) == len(vistos) == len(pcs) - len(repetidos),
         f"{len(filas)} filas · {len(pcs)} avisos · {len(repetidos)} repetidos"),
        ("todo homologado a UF", not sin_uf, f"{len(sin_uf)} sin Precio UF"),
        ("0 precios <= 0", not no_pos, f"{len(no_pos)} con precio <= 0"),
        ("cada vacío está declarado en Datos faltantes", not mal_falt,
         f"{len(mal_falt)} filas donde no coincide"),
    ]
    return salida, filas, chequeos, snap


def verificar(carpeta, dump, muestra=False):
    """compara lo que quedo en Notion contra lo que este script esperaba.

    Con muestra=True no exige que esten todas: exige que las que estan sean
    exactamente las esperadas, y deja dicho cuantas faltan. El item 05 no cierra
    hasta que falten cero.
    """
    esperado = json.loads((carpeta / "02-filas.json").read_text(encoding="utf-8"))
    filas = {f["ID del portal"]: f for f in esperado["filas"]}
    ruta = Path(dump)
    if ruta.suffix == ".csv":
        # id,precio_uf,precio_publicado,m2,dormitorios,baños,moneda
        col = ["ID del portal", "Precio UF", "Precio publicado", "m²",
               "Dormitorios", "Baños", "Moneda publicada"]
        notion = []
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            v = linea.split(",")
            notion.append({c: (None if x == "" else x) for c, x in zip(col, v)})
    else:
        notion = json.loads(ruta.read_text(encoding="utf-8"))
    en_notion = {f.get("ID del portal"): f for f in notion}

    faltan = set(filas) - set(en_notion)
    sobran = set(en_notion) - set(filas)
    difieren = []
    for i, f in filas.items():
        n = en_notion.get(i)
        if not n:
            continue
        for col in ("Precio UF", "m²", "Precio publicado", "Dormitorios", "Baños"):
            a, b = f.get(col), n.get(col)
            if a is None and b in (None, ""):
                continue
            if a is None or b is None or abs(float(a) - float(b)) > 0.01:
                difieren.append((i, col, a, b))
    no_uf = [i for i, n in en_notion.items() if n.get("Moneda publicada") is None
             or n.get("Precio UF") in (None, "")]
    no_pos = [i for i, n in en_notion.items() if float(n.get("Precio UF") or 0) <= 0]
    completo = ("filas en Notion == filas del snapshot post-dedup",
                len(en_notion) == len(filas) and not faltan and not sobran,
                f"{len(en_notion)} en Notion · {len(filas)} esperadas · "
                f"faltan {len(faltan)} · sobran {len(sobran)}")
    if muestra:
        completo = ("las filas cargadas son un subconjunto exacto de las esperadas",
                    not sobran,
                    f"{len(en_notion)} cargadas de {len(filas)} · 0 sobran · "
                    f"faltan {len(faltan)} para que el item 05 cierre")
    return [
        completo,
        ("precio y m² coinciden fila por fila", not difieren,
         f"{len(difieren)} diferencias" + (f" · ej: {difieren[:2]}" if difieren else "")),
        ("todo homologado a UF", not no_uf, f"{len(no_uf)} sin Precio UF o sin moneda"),
        ("0 precios <= 0", not no_pos, f"{len(no_pos)} con precio <= 0"),
    ]


def anotar_manifest(carpeta, entrada):
    m = json.loads((carpeta / "manifest.json").read_text(encoding="utf-8"))
    m["agentes"] = [a for a in m["agentes"] if a["agente"] != "cargador"] + [entrada]
    (carpeta / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="cargador — snapshot a filas de Notion")
    ap.add_argument("--corrida", help="carpeta de runs/ (por defecto, la última)")
    ap.add_argument("--uf", type=float, help="valor de la UF del día")
    ap.add_argument("--fecha-uf", help="YYYY-MM-DD")
    ap.add_argument("--fuente-uf", help="de dónde salió")
    ap.add_argument("--verificar", help="JSON o CSV con las filas leídas de Notion")
    ap.add_argument("--muestra", action="store_true",
                    help="se cargó sólo una parte: no exige que estén todas")
    a = ap.parse_args()
    carpeta = Path(a.corrida) if a.corrida else ultima_corrida()

    if a.verificar:
        chequeos = verificar(carpeta, a.verificar, a.muestra)
        print(f"cargador · verificación contra Notion · {carpeta}\n")
    else:
        if not (a.uf and a.fecha_uf and a.fuente_uf):
            raise SystemExit("ROJO · faltan --uf, --fecha-uf y --fuente-uf. "
                             "No hay default: un default sería un número inventado.")
        salida, filas, chequeos, snap = transformar(carpeta, a.uf, a.fecha_uf, a.fuente_uf)
        anotar_manifest(carpeta, {
            "agente": "cargador",
            "leyo": ["01-snapshot.json"],
            "escribio": [salida.name, "Notion · base Propiedades (lo escribe el agente por MCP)"],
            "uf": {"valor": a.uf, "fecha": a.fecha_uf, "fuente": a.fuente_uf},
            "filas": len(filas),
            "en_clp_homologadas": sum(1 for f in filas if f["Moneda publicada"] == "CLP"),
            "chequeos": [{"nombre": n, "verde": bool(ok), "detalle": d} for n, ok, d in chequeos],
        })
        print(f"cargador · {carpeta} · UF {a.uf} del {a.fecha_uf}")
        print(f"{len(filas)} filas · {sum(1 for f in filas if f['Moneda publicada']=='CLP')} "
              f"homologadas de CLP a UF")
        print(f"escrito: {salida}\n")

    for n, ok, d in chequeos:
        print(f"  {'VERDE' if ok else 'ROJO '}  {n}  · {d}")
    rojos = [n for n, ok, _ in chequeos if not ok]
    if rojos:
        print("\nROJO · " + "; ".join(rojos))
        return 1
    print("\nVERDE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

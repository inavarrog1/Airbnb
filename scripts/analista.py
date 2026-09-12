#!/usr/bin/env python
"""analista — agente 3 de los seis.

Parte de las filas cargadas en Notion. Termina con un ranking por tipologia.

CERO SUPUESTOS FINANCIEROS. Solo aritmetica sobre lo observado: una division,
una mediana y un conteo. Nada de acá depende de creerle a una tarifa, a una
ocupacion ni a una tasa.

No existe ni va a existir una columna de score compuesto: un puntaje unico
esconde la decision adentro de un numero que despues nadie puede discutir.

    .venv/bin/python scripts/analista.py runs/<corrida>/04-para-analizar.json
"""
import json, statistics, sys
from pathlib import Path

MINIMO_PARA_PERCENTIL = 5      # specs.md · un grupo mas chico no reporta percentil

# las unicas columnas que este agente produce. Si aparece una que no esta acá,
# el chequeo de "sin score compuesto" da rojo.
COLUMNAS = {"id", "tipologia", "tipo_m2", "grupo", "precio_uf", "m2", "uf_m2",
            "mediana_uf_m2_del_grupo", "percentil_en_su_grupo",
            "tamano_del_grupo", "grupo_chico", "posicion_en_el_grupo"}


def clave_de_grupo(f):
    """La tipologia, y dentro de ella el tipo de m².

    specs.md dice agrupar por tipologia: un 1D1B no se compara contra un 2D2B.
    El tipo de m² entra por la misma razon: 90 m² utiles y 90 m² totales no son
    la misma superficie, y un UF/m² que los mezcla compara dos cosas distintas.
    """
    return f"{f['tipologia']} · {f['tipo_m2']}"


def analizar(entrada):
    filas = json.loads(Path(entrada).read_text(encoding="utf-8"))

    # --- quien entra al ranking y quien no, declarado ---
    dentro, fuera = [], []
    for f in filas:
        falta = []
        if f.get("tipo_aviso") == "proyecto":
            falta.append("es un proyecto: precio 'Desde' y atributos en rango")
        if not f.get("tipologia"):
            falta.append("sin tipologia")
        if not f.get("m2"):
            falta.append("sin m²")
        if not f.get("precio_uf"):
            falta.append("sin precio en UF")
        (fuera if falta else dentro).append(
            {**f, "motivo": " · ".join(falta)} if falta else f)

    # --- la unica aritmetica: precio entre metros ---
    for f in dentro:
        f["uf_m2"] = round(f["precio_uf"] / f["m2"], 2)
        f["grupo"] = clave_de_grupo(f)

    grupos = {}
    for f in dentro:
        grupos.setdefault(f["grupo"], []).append(f)

    salida = []
    for grupo, gs in grupos.items():
        gs.sort(key=lambda x: x["uf_m2"])          # ordenado dentro del grupo
        n = len(gs)
        mediana = round(statistics.median([x["uf_m2"] for x in gs]), 2)
        for i, f in enumerate(gs, start=1):
            menores = sum(1 for x in gs if x["uf_m2"] < f["uf_m2"])
            salida.append({
                "id": f["id"],
                "tipologia": f["tipologia"],
                "tipo_m2": f["tipo_m2"],
                "grupo": grupo,
                "precio_uf": f["precio_uf"],
                "m2": f["m2"],
                "uf_m2": f["uf_m2"],
                "mediana_uf_m2_del_grupo": mediana,
                # porcentaje del grupo con un UF/m² MENOR que el de esta propiedad.
                # 0 = la mas barata por m² de su tipologia. No dice "mejor": dice
                # donde cae en la distribucion de su grupo.
                "percentil_en_su_grupo": (round(100 * menores / n, 1)
                                          if n >= MINIMO_PARA_PERCENTIL else None),
                "tamano_del_grupo": n,
                "grupo_chico": n < MINIMO_PARA_PERCENTIL,
                "posicion_en_el_grupo": i,
            })
    return salida, fuera, grupos


def chequear(salida, fuera, grupos, filas_entrada):
    def recalcula_igual(f):
        return abs(round(f["precio_uf"] / f["m2"], 2) - f["uf_m2"]) < 0.01
    medianas_ok = all(
        abs(round(statistics.median([x["uf_m2"] for x in gs]), 2)
            - next(s["mediana_uf_m2_del_grupo"] for s in salida if s["grupo"] == g)) < 0.01
        for g, gs in grupos.items())
    chicos_con_percentil = [f for f in salida
                            if f["grupo_chico"] and f["percentil_en_su_grupo"] is not None]
    grandes_sin_percentil = [f for f in salida
                             if not f["grupo_chico"] and f["percentil_en_su_grupo"] is None]
    columnas_de_mas = set().union(*[set(f) for f in salida]) - COLUMNAS if salida else set()
    return [
        ("los ratios recalculados dan igual a los guardados",
         all(recalcula_igual(f) for f in salida), f"{len(salida)} ratios"),
        ("las medianas recalculadas dan igual a las guardadas", medianas_ok,
         f"{len(grupos)} grupos"),
        (f"ningun grupo de menos de {MINIMO_PARA_PERCENTIL} reporta percentil",
         not chicos_con_percentil, f"{len(chicos_con_percentil)} violaciones"),
        ("todo grupo suficientemente grande si reporta percentil",
         not grandes_sin_percentil, f"{len(grandes_sin_percentil)} faltantes"),
        ("no existe ninguna columna de score compuesto", not columnas_de_mas,
         str(columnas_de_mas) if columnas_de_mas else "solo columnas declaradas"),
        ("cada propiedad esta o en el ranking o declarada afuera con su motivo",
         len(salida) + len(fuera) == len(filas_entrada) and all(f["motivo"] for f in fuera),
         f"{len(salida)} en el ranking + {len(fuera)} afuera = {len(filas_entrada)}"),
    ]


def main():
    entrada = Path(sys.argv[1] if len(sys.argv) > 1
                   else "runs/2026-09-12-1210-2/04-para-analizar.json")
    filas = json.loads(entrada.read_text(encoding="utf-8"))
    salida, fuera, grupos = analizar(entrada)
    destino = entrada.parent / "05-ranking.json"
    destino.write_text(json.dumps(
        {"agente": "analista", "entrada": entrada.name,
         "minimo_para_percentil": MINIMO_PARA_PERCENTIL,
         "en_el_ranking": len(salida), "fuera_del_ranking": fuera,
         "ranking": salida}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"analista · {len(filas)} propiedades leidas · {len(salida)} en el ranking · "
          f"{len(fuera)} afuera\n")
    print(f"{'GRUPO':<22} {'n':>3}  {'mediana':>8}  {'min':>8}  {'max':>8}   percentil")
    for g in sorted(grupos, key=lambda x: -len(grupos[x])):
        gs = sorted(grupos[g], key=lambda x: x["uf_m2"])
        n = len(gs)
        med = round(statistics.median([x["uf_m2"] for x in gs]), 2)
        print(f"{g:<22} {n:>3}  {med:>8.2f}  {gs[0]['uf_m2']:>8.2f}  {gs[-1]['uf_m2']:>8.2f}   "
              f"{'si' if n >= MINIMO_PARA_PERCENTIL else 'NO — grupo chico'}")
    print(f"\nafuera del ranking ({len(fuera)}):")
    for f in fuera:
        print(f"  {f['id']}  {f['motivo']}")
    print()
    for n, ok, d in chequear(salida, fuera, grupos, filas):
        print(f"  {'VERDE' if ok else 'ROJO '}  {n}  · {d}")
    rojos = [n for n, ok, _ in chequear(salida, fuera, grupos, filas) if not ok]
    print(f"\n{'ROJO · ' + '; '.join(rojos) if rojos else 'VERDE'}")
    print(f"escrito: {destino}")
    return 1 if rojos else 0


if __name__ == "__main__":
    sys.exit(main())

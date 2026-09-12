#!/usr/bin/env python
"""Arma evaluador.html: un archivo, sin dependencias, que abre con doble clic.

Inyecta en la plantilla los supuestos, el ranking y el hash de supuestos.yaml.
Los datos no se transcriben a mano: se leen de los archivos.

    .venv/bin/python scripts/construir_evaluador.py
"""
import hashlib, json, sys
from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parent.parent


def ultimo_ranking():
    cs = sorted(RAIZ.glob("runs/*/05-ranking.json"))
    if not cs:
        raise SystemExit("ROJO · no hay ningun 05-ranking.json en runs/")
    return cs[-1]


def main():
    sup_path = RAIZ / "supuestos.yaml"
    if not sup_path.exists():
        raise SystemExit("ROJO · falta supuestos.yaml (item 07)")
    crudo = sup_path.read_bytes()
    supuestos = yaml.safe_load(crudo.decode("utf-8"))
    hash_sup = hashlib.sha256(crudo).hexdigest()

    rank_path = ultimo_ranking()
    rank = json.loads(rank_path.read_text(encoding="utf-8"))
    props = [{"id": x["id"], "tipologia": x["tipologia"], "precio_uf": x["precio_uf"],
              "m2": x["m2"], "uf_m2": x["uf_m2"],
              "percentil": x["percentil_en_su_grupo"], "grupo": x["grupo"]}
             for x in rank["ranking"]]
    # el ranking ya viene ordenado dentro de cada grupo; se ofrece de mas barato
    # por m² a mas caro, sin mezclar grupos
    props.sort(key=lambda p: (p["grupo"], p["uf_m2"]))

    datos = {"supuestos": supuestos, "propiedades": props,
             "hash_supuestos": hash_sup, "corrida": rank_path.parent.name,
             "generado": "construir_evaluador.py"}

    html = (RAIZ / "plantillas" / "evaluador.html").read_text(encoding="utf-8")
    if "__DATOS__" not in html:
        raise SystemExit("ROJO · la plantilla no tiene el marcador __DATOS__")
    salida = RAIZ / "evaluador.html"
    salida.write_text(html.replace("__DATOS__", json.dumps(datos, ensure_ascii=False)),
                      encoding="utf-8")

    texto = salida.read_text(encoding="utf-8")
    chequeos = [
        ("es un solo archivo, sin dependencias externas",
         "src=" not in texto and "href=" not in texto and "@import" not in texto,
         f"{salida.stat().st_size // 1024} KB"),
        ("no pide nada por red al abrirse",
         "fetch(" not in texto and "XMLHttpRequest" not in texto, "0 llamadas de red"),
        ("registra el hash de supuestos.yaml", hash_sup[:16] in texto, hash_sup[:16] + "…"),
        ("la UF viene con su fecha",
         str(supuestos["uf"]["valor"]) in texto and str(supuestos["uf"]["fecha"]) in texto,
         f"{supuestos['uf']['valor']} del {supuestos['uf']['fecha']}"),
        ("trae las propiedades del ranking", len(props) > 0, f"{len(props)} propiedades"),
        ("declara si los supuestos estan firmados",
         supuestos["firma"]["estado"] in texto, supuestos["firma"]["estado"]),
    ]
    print(f"evaluador.html · {salida.stat().st_size // 1024} KB · "
          f"{len(props)} propiedades · supuestos {supuestos['firma']['estado']}\n")
    for n, ok, d in chequeos:
        print(f"  {'VERDE' if ok else 'ROJO '}  {n}  · {d}")
    rojos = [n for n, ok, _ in chequeos if not ok]
    print("\n" + ("ROJO · " + "; ".join(rojos) if rojos else "VERDE"))
    return 1 if rojos else 0


if __name__ == "__main__":
    sys.exit(main())

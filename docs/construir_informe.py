"""Construye el informe: rellena docs/informe_fuente.md con los resultados REALES de results/,
y genera docs/INFORME.md, docs/INFORME.html y docs/INFORME.pdf (con Edge o Chrome sin ventana).

Uso:  python docs/construir_informe.py
Antes conviene ejecutar: pytest, bench/run_benchmarks.py, bench/demo_escenas.py,
game/capturas_escenas.py y docs/figuras.py (ver Anexo A del informe).
"""
import csv
import os
import re
import statistics as st
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
DOCS = os.path.join(RAIZ, "docs")
RES = os.path.join(RAIZ, "results")

import markdown

from core.graph import construir_grafo
from sim.mapgen import generar_mapa

NAVEGADORES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
               r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
               r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]


def f(x, d=1):
    """Número con coma decimal (formato español)."""
    return f"{x:.{d}f}".replace(".", ",")


def leer(nombre):
    with open(os.path.join(RES, nombre), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def tabla(cabecera, filas):
    out = ["| " + " | ".join(cabecera) + " |", "|" + "---|" * len(cabecera)]
    out += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(out)


def valores():
    v = {}
    v["FECHA"] = "27 de noviembre de 2026"
    pruebas = open(os.path.join(RES, "pruebas.txt"), encoding="utf-8", errors="replace").read()
    v["PRUEBAS_TXT"] = pruebas.strip()
    m = re.search(r"(\d+) passed", pruebas)
    v["N_PRUEBAS"] = m.group(1) if m else "?"
    v["ESCENAS_TXT"] = open(os.path.join(RES, "escenas.txt"), encoding="utf-8").read().strip()
    bench = leer("benchmarks.csv")
    v["EQUIPO"] = bench[0]["equipo"]

    # Tamaño de los grafos (semilla 11).
    filas = []
    for t in (20, 40, 80, 160):
        mapa = generar_mapa(11, t, t)
        g = construir_grafo(mapa)
        filas.append([f"{t}×{t}", g.V, g.E, len(mapa.salas), len(mapa.puertas), f(g.E / g.V, 2)])
    v["TABLA_VE"] = tabla(["Mapa", "V (vértices)", "E (aristas)", "Salas", "Puertas", "E / V"], filas)

    # Dijkstra vs A*.
    res = {(r["tamano"], r["algoritmo"]): r for r in leer("resumen.csv")}
    filas, ratios = [], []
    for t in ("20", "40", "80", "160"):
        d, a = res[(t, "Dijkstra")], res[(t, "A*")]
        ratios.append(float(d["nodos_medios"]) / float(a["nodos_medios"]))
        filas.append([f"{t}×{t}", f(float(d["tiempo_medio_ms"]), 3), f(float(d["nodos_medios"])), f(float(d["memoria_media_kb"])),
                      f(float(a["tiempo_medio_ms"]), 3), f(float(a["nodos_medios"])), f(float(a["memoria_media_kb"])),
                      d["muestras"]])
    v["TABLA_ALGS"] = tabla(["Mapa", "Dijkstra ms", "Dijkstra nodos", "Dijkstra KB", "A\\* ms", "A\\* nodos", "A\\* KB",
                             "Muestras"], filas)
    v["RATIO_MIN"], v["RATIO_MAX"] = f(min(ratios)), f(max(ratios))
    d, a = res[("160", "Dijkstra")], res[("160", "A*")]
    v["PCT_NODOS_160"] = f(100 * (1 - float(a["nodos_medios"]) / float(d["nodos_medios"])), 0)
    v["VEL_160"] = f(float(d["tiempo_medio_ms"]) / float(a["tiempo_medio_ms"]))

    # Partidas reales.
    p = {r["algoritmo"]: r for r in leer("partidas.csv")}
    pd, pa = p["Dijkstra"], p["A*"]
    v["TABLA_PARTIDAS"] = tabla(
        ["Algoritmo", "Búsquedas", "Tiempo medio (ms)", "Nodos medios", "Costo medio"],
        [[k, r["busquedas"], f(float(r["tiempo_medio_ms"]), 4), f(float(r["nodos_medios"])), f(float(r["costo_medio"]), 2)]
         for k, r in (("Dijkstra", pd), ("A\\*", pa))])
    v["PCT_NODOS_PARTIDAS"] = f(100 * (1 - float(pa["nodos_medios"]) / float(pd["nodos_medios"])), 0)
    v["PCT_TIEMPO_PARTIDAS"] = f(100 * (1 - float(pa["tiempo_medio_ms"]) / float(pd["tiempo_medio_ms"])), 0)

    # Cobertura.
    cob = leer("cobertura.csv")
    filas, med = [], {}
    for nox in ("caminando", "corriendo"):
        for c in ("fija", "dinamica"):
            xs = [int(r["ticks_hasta_deteccion"]) for r in cob if r["cobertura"] == c and r["nox"] == nox]
            det = sum(int(r["detectado"]) for r in cob if r["cobertura"] == c and r["nox"] == nox)
            med[(c, nox)] = st.mean(xs)
            filas.append([{"fija": "Fija", "dinamica": "Dinámica"}[c], nox, f(st.mean(xs)), f(st.median(xs)), f"{det} / {len(xs)}"])
    v["TABLA_COBERTURA"] = tabla(["Cobertura", "Nox", "Ticks medios hasta detección", "Mediana", "Detecciones"], filas)
    v["COB_DIN_CORR"], v["COB_FIJA_CORR"] = f(med[("dinamica", "corriendo")]), f(med[("fija", "corriendo")])
    return v


CSS = """
@page { size: A4; margin: 22mm 18mm 22mm 18mm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #666; }
        @top-right { content: "Protocolo Sombra · Algoritmos Computacionales"; font-size: 8pt; color: #888; } }
@page :first { @bottom-center { content: ""; } @top-right { content: ""; } }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1c1c1c; }
h1 { font-size: 20pt; color: #1f3a5f; border-bottom: 2px solid #1f3a5f; padding-bottom: 4px; }
h2 { font-size: 15pt; color: #1f3a5f; margin-top: 22px; border-bottom: 1px solid #c9d3e0; padding-bottom: 3px; page-break-after: avoid; }
h3 { font-size: 12pt; color: #2f4b7c; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.2pt; page-break-inside: avoid; }
th { background: #1f3a5f; color: #fff; padding: 5px 6px; text-align: left; }
td { border: 1px solid #c9d3e0; padding: 4px 6px; vertical-align: top; }
tr:nth-child(even) td { background: #f4f7fb; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #eef1f6; padding: 0 3px; border-radius: 3px; }
pre { background: #f4f6fa; border: 1px solid #d5dbe6; border-radius: 4px; padding: 8px; font-size: 8.3pt; line-height: 1.3;
      white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
img { max-width: 100%; display: block; margin: 8px auto; page-break-inside: avoid; }
p img + em { display: block; text-align: center; }
.portada { height: 245mm; text-align: center; page-break-after: always; display: flex; flex-direction: column;
           justify-content: center; align-items: center; }
.portada h1 { border: none; font-size: 30pt; margin: 0; }
.portada .sub { font-size: 14pt; color: #444; margin: 6px 0 40px; }
.portada .uni { font-size: 15pt; font-weight: 600; color: #1f3a5f; }
.portada .bloque { margin-top: 28px; font-size: 12pt; line-height: 1.7; }
.portada .linea { width: 120px; border-top: 3px solid #1f3a5f; margin: 18px auto; }
"""


def portada():
    return """<div class="portada">
<div class="uni">FUNDACIÓN UNIVERSITARIA DE POPAYÁN</div>
<div>Algoritmos Computacionales · Proyecto final</div>
<div class="linea"></div>
<h1>Protocolo Sombra</h1>
<div class="sub">Infiltración y vigilancia con agentes autónomos<br>Informe técnico: diseño, análisis de complejidad y resultados experimentales</div>
<div class="bloque"><b>Integrantes</b><br>Sebastian Mamian Palta<br>Hernando Andres Peña<br>Keymmer Kaleth Meneses<br>Juan David Erazo Meneses</div>
<div class="bloque"><b>Docente</b><br>Andrés Felipe Arboleda</div>
<div class="bloque">Popayán · 27 de noviembre de 2026<br>Repositorio: github.com/hiTimmyy/protocolo-sombra</div>
</div>"""


def main():
    v = valores()
    fuente = open(os.path.join(DOCS, "informe_fuente.md"), encoding="utf-8").read()
    for k, val in v.items():
        fuente = fuente.replace("{{" + k + "}}", str(val))
    pendientes = re.findall(r"\{\{[A-Z_0-9]+\}\}", fuente)
    assert not pendientes, f"Marcadores sin rellenar: {pendientes}"
    open(os.path.join(DOCS, "INFORME.md"), "w", encoding="utf-8").write(fuente)

    cuerpo = fuente.split("<!--FIN-PORTADA-->", 1)[1]
    html_cuerpo = markdown.markdown(cuerpo, extensions=["tables", "fenced_code", "sane_lists"])
    html = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Protocolo Sombra - Informe</title>'
            f"<style>{CSS}</style></head><body>{portada()}{html_cuerpo}</body></html>")
    ruta_html = os.path.join(DOCS, "INFORME.html")
    open(ruta_html, "w", encoding="utf-8").write(html)

    navegador = next((n for n in NAVEGADORES if os.path.exists(n)), None)
    if not navegador:
        print("No se encontró Edge/Chrome: se generó INFORME.md e INFORME.html (imprima el HTML a PDF).")
        return
    ruta_pdf = os.path.join(DOCS, "INFORME.pdf")
    subprocess.run([navegador, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={ruta_pdf}", "file:///" + ruta_html.replace("\\", "/")],
                   check=True, capture_output=True, timeout=120)
    print("Generados:", ruta_html, "y", ruta_pdf)


if __name__ == "__main__":
    main()

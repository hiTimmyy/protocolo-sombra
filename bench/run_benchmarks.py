"""Benchmarks sin ventana: Dijkstra vs A* y cobertura fija vs dinámica.

Uso:  python bench/run_benchmarks.py
Genera en results/: benchmarks.csv, resumen.csv, cobertura.csv y gráficas .png.
"""
from __future__ import annotations

import csv
import os
import platform
import random
import statistics as st
import sys
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core.graph import construir_grafo
from core.pathfinding import a_estrella, dijkstra
from sim.contract import Accion
from sim.mapgen import generar_mapa
from sim.simulation import Config, Simulation

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
TAMANOS = [20, 40, 80, 160]
SEMILLAS = [11, 22, 33]
PARES_POR_MAPA = 3
REPETICIONES = 5
EQUIPO = f"{platform.system()} {platform.release()} {platform.machine()} Python {platform.python_version()}"
ALGORITMOS = {"Dijkstra": dijkstra, "A*": a_estrella}


def benchmark_pathfinding():
    filas = []
    for tam in TAMANOS:
        for seed in SEMILLAS:
            mapa = generar_mapa(seed, tam, tam)           # mismo mapa/costos para ambos algoritmos
            grafo = construir_grafo(mapa)
            rng = random.Random(seed * 1000 + tam)
            vertices = sorted(grafo.ady)
            pares = [(rng.choice(vertices), rng.choice(vertices)) for _ in range(PARES_POR_MAPA)]
            for k, (o, d) in enumerate(pares):            # mismos orígenes/destinos
                costos = {}
                for nombre, alg in ALGORITMOS.items():
                    for rep in range(REPETICIONES):
                        r = alg(grafo, o, d)               # tiempo sin tracemalloc
                        tracemalloc.start()
                        alg(grafo, o, d)
                        pico = tracemalloc.get_traced_memory()[1]
                        tracemalloc.stop()
                        costos[nombre] = r.costo
                        filas.append([EQUIPO, seed, tam, k, nombre, rep, f"{r.tiempo_s:.6f}",
                                      r.costo, r.nodos_expandidos, round(pico / 1024, 1)])
                assert costos["Dijkstra"] == costos["A*"], f"Costos distintos: {costos} ({tam},{seed},{k})"
    return filas


def resumir(filas):
    resumen = []
    for tam in TAMANOS:
        for nombre in ALGORITMOS:
            f = [x for x in filas if x[2] == tam and x[4] == nombre]
            resumen.append([tam, nombre, round(st.mean(float(x[6]) for x in f) * 1000, 3),
                            round(st.mean(x[8] for x in f), 1), round(st.mean(x[9] for x in f), 1), len(f)])
    return resumen


def jugar_bot(seed: int, cobertura: str, max_ticks: int = 600):
    """Nox automática (corre hacia la terminal por Dijkstra). Devuelve el tick de la primera
    detección visual por un guardia (o None si no la hubo en `max_ticks`)."""
    sim = Simulation(seed, Config(cobertura=cobertura))
    destino = sim.mapa.terminal
    for _ in range(max_ticks):
        if sim.resultado != "jugando":
            return None
        nox = sim.nox.pos
        if abs(nox[0] - destino[0]) + abs(nox[1] - destino[1]) <= 1:
            accion = Accion(interactuar=True)
        else:
            r = dijkstra(sim.grafo, nox, destino)
            sig = r.ruta[1]
            dir_ = {(0, -1): "arriba", (0, 1): "abajo", (-1, 0): "izquierda", (1, 0): "derecha"}[
                (sig[0] - nox[0], sig[1] - nox[1])]
            accion = Accion(mover=dir_, correr=True)
        sim.step(accion)
        if any(g.estado == "ALERTA" for g in sim.guardias):
            return sim.tick
    return None


def comparar_cobertura(semillas=range(1, 21), max_ticks=600):
    """Cobertura fija (patrullas fijas, solo visión propia) vs dinámica (reacciona a ruido y bus)."""
    filas = []
    for seed in semillas:
        for cob in ("fija", "dinamica"):
            t = jugar_bot(seed, cob, max_ticks)
            filas.append([seed, cob, t if t is not None else max_ticks, int(t is not None)])
    return filas


def guardar_csv(nombre, cabecera, filas):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, nombre), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        w.writerows(filas)


def graficas(resumen, cob):
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for nombre in ALGORITMOS:
        r = [x for x in resumen if x[1] == nombre]
        ax[0].plot([x[0] for x in r], [x[2] for x in r], marker="o", label=nombre)
        ax[1].plot([x[0] for x in r], [x[3] for x in r], marker="o", label=nombre)
    ax[0].set(title="Tiempo medio de búsqueda", xlabel="Tamaño del mapa (N x N)", ylabel="ms", yscale="log")
    ax[1].set(title="Nodos expandidos (media)", xlabel="Tamaño del mapa (N x N)", ylabel="nodos", yscale="log")
    for a in ax:
        a.legend(), a.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "grafica_dijkstra_vs_astar.png"), dpi=120)
    plt.close(fig)
    medias = {c: st.mean(f[2] for f in cob if f[1] == c) for c in ("fija", "dinamica")}
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(list(medias), list(medias.values()), color=["#888", "#c33"])
    ax.set(title="Ticks hasta que un guardia ve a Nox", ylabel="ticks (menor = mejor)")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "grafica_cobertura.png"), dpi=120)
    plt.close(fig)
    return medias


def main():
    print(f"Equipo: {EQUIPO}")
    filas = benchmark_pathfinding()
    guardar_csv("benchmarks.csv", ["equipo", "semilla", "tamano", "par", "algoritmo", "repeticion",
                                   "tiempo_s", "costo", "nodos_expandidos", "memoria_pico_kb"], filas)
    resumen = resumir(filas)
    guardar_csv("resumen.csv", ["tamano", "algoritmo", "tiempo_medio_ms", "nodos_medios", "memoria_media_kb",
                                "muestras"], resumen)
    print("OK: el costo de A* es igual al de Dijkstra en todas las condiciones.")
    for r in resumen:
        print(f"  {r[0]:>4}x{r[0]:<4} {r[1]:<9} {r[2]:>9.3f} ms  {r[3]:>9.1f} nodos  {r[4]:>8.1f} KB")
    cob = comparar_cobertura()
    guardar_csv("cobertura.csv", ["semilla", "cobertura", "ticks_hasta_deteccion", "detectado"], cob)
    medias = graficas(resumen, cob)
    for c, v in medias.items():
        det = sum(f[3] for f in cob if f[1] == c)
        print(f"  cobertura {c:<8}: {v:.1f} ticks hasta ver a Nox ({det}/{len(cob)//2} detecciones)")
    print(f"Resultados en {RESULTS}")


if __name__ == "__main__":
    main()

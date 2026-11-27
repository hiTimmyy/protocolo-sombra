"""Dijkstra y A* deben dar el mismo costo (y respetar costos de alfombra y puertas)."""
import random

from core.graph import Mapa, construir_grafo
from core.pathfinding import a_estrella, dijkstra
from sim.mapgen import generar_mapa


def test_mismo_costo_en_mapas_generados():
    rng = random.Random(7)
    for seed in range(5):
        g = construir_grafo(generar_mapa(seed, 30, 20))
        vs = sorted(g.ady)
        for _ in range(15):
            a, b = rng.choice(vs), rng.choice(vs)
            rd, ra = dijkstra(g, a, b), a_estrella(g, a, b)
            assert rd.costo == ra.costo


def test_alfombra_y_puerta_bloqueada():
    m = Mapa.desde_ascii([
        "#######",
        "#.,,,.#",   # camino de arriba: alfombra (costo 2 por casilla)
        "#.###.#",
        "#.D...#",
        "#######",
    ])
    g = construir_grafo(m)
    assert dijkstra(g, (1, 1), (5, 1)).costo == a_estrella(g, (1, 1), (5, 1)).costo == 7
    m.puertas[0].estado = "bloqueada"
    g2 = construir_grafo(m)
    r = a_estrella(g2, (1, 3), (5, 3))
    assert r.ruta and (2, 3) not in r.ruta      # rodea por la alfombra
    assert r.costo == dijkstra(g2, (1, 3), (5, 3)).costo == 11


def test_sin_camino():
    g = construir_grafo(Mapa.desde_ascii(["#.#.#"]))
    assert dijkstra(g, (1, 0), (3, 0)).ruta == [] and a_estrella(g, (1, 0), (3, 0)).ruta == []

"""Dijkstra y A* sobre el mismo grafo (lista de adyacencia, heapq).

Ambos devuelven `Resultado` con ruta (incluye origen y destino; [] si no hay
camino), costo (inf si no hay), nodos_expandidos y tiempo_s.

Heurística Manhattan: admisible y consistente porque el costo mínimo de un paso
es 1 y un paso cambia la distancia Manhattan en exactamente 1:
h(a) <= costo(a,b) + h(b). Por eso A* con lista cerrada es óptimo.
"""
from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from core.graph import Grafo

Pos = Tuple[int, int]
INF = float("inf")


@dataclass
class Resultado:
    ruta: List[Pos] = field(default_factory=list)
    costo: float = INF
    nodos_expandidos: int = 0
    tiempo_s: float = 0.0


def manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reconstruir(previo: Dict[Pos, Pos], destino: Pos) -> List[Pos]:
    ruta = [destino]
    while ruta[-1] in previo:
        ruta.append(previo[ruta[-1]])
    ruta.reverse()
    return ruta


def dijkstra(grafo: Grafo, origen: Pos, destino: Pos) -> Resultado:
    """Camino de costo mínimo. Expande por menor g (costo acumulado)."""
    t0 = time.perf_counter()
    res = Resultado()
    if origen not in grafo.ady or destino not in grafo.ady:
        res.tiempo_s = time.perf_counter() - t0
        return res
    dist: Dict[Pos, float] = {origen: 0}
    previo: Dict[Pos, Pos] = {}
    cerrados = set()
    cola = [(0, origen)]
    while cola:
        g, u = heapq.heappop(cola)
        if u in cerrados:          # entrada obsoleta (borrado perezoso)
            continue
        cerrados.add(u)
        res.nodos_expandidos += 1
        if u == destino:
            res.ruta, res.costo = _reconstruir(previo, destino), g
            break
        for v, c in grafo.ady[u]:
            ng = g + c
            if ng < dist.get(v, INF):
                dist[v] = ng
                previo[v] = u
                heapq.heappush(cola, (ng, v))
    res.tiempo_s = time.perf_counter() - t0
    return res


def a_estrella(grafo: Grafo, origen: Pos, destino: Pos, h=manhattan) -> Resultado:
    """A*: expande por menor f = g + h(n, destino). Con h = Manhattan es óptimo."""
    t0 = time.perf_counter()
    res = Resultado()
    if origen not in grafo.ady or destino not in grafo.ady:
        res.tiempo_s = time.perf_counter() - t0
        return res
    dist: Dict[Pos, float] = {origen: 0}
    previo: Dict[Pos, Pos] = {}
    cerrados = set()
    cola = [(h(origen, destino), 0, origen)]   # (f, g, nodo)
    while cola:
        _, g, u = heapq.heappop(cola)
        if u in cerrados:
            continue
        cerrados.add(u)
        res.nodos_expandidos += 1
        if u == destino:
            res.ruta, res.costo = _reconstruir(previo, destino), g
            break
        for v, c in grafo.ady[u]:
            ng = g + c
            if ng < dist.get(v, INF):
                dist[v] = ng
                previo[v] = u
                heapq.heappush(cola, (ng + h(v, destino), ng, v))
    res.tiempo_s = time.perf_counter() - t0
    return res

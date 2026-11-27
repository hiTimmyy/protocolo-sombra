"""DFS recursivo con profundidad limitada: enumera rutas simples desde un punto.

Se usa para generar rutas/puntos candidatos de búsqueda de un guardia.
Complejidad: tiempo O(b^d) (b = ramificación, d = profundidad máxima);
pila de llamadas O(d).
"""
from __future__ import annotations

from typing import List, Tuple

from core.graph import Grafo

Pos = Tuple[int, int]


def rutas_dfs(grafo: Grafo, inicio: Pos, profundidad_max: int,
              max_rutas: int = 2000) -> Tuple[List[List[Pos]], int]:
    """Devuelve (rutas, llamadas). Cada ruta es un camino simple (sin repetir casillas)
    que termina al agotar `profundidad_max` pasos o al no tener vecinos sin visitar.

    Caso base: se alcanzó la profundidad límite o no hay vecino nuevo.
    Progreso: cada llamada recursiva agrega una casilla (profundidad + 1), así que
    la recursión siempre termina en a lo sumo `profundidad_max` niveles.
    `max_rutas` es un tope de seguridad contra explosión combinatoria.
    """
    if profundidad_max < 0:
        raise ValueError("profundidad_max debe ser >= 0")
    rutas: List[List[Pos]] = []
    llamadas = 0
    camino = [inicio]
    visitados = {inicio}

    def dfs(profundidad: int) -> None:
        nonlocal llamadas
        llamadas += 1
        if len(rutas) >= max_rutas:
            return
        if profundidad == profundidad_max:          # caso base 1: límite de profundidad
            rutas.append(list(camino))
            return
        hubo_vecino = False
        for v, _ in grafo.ady.get(camino[-1], ()):
            if v not in visitados:
                hubo_vecino = True
                visitados.add(v)
                camino.append(v)
                dfs(profundidad + 1)                # paso recursivo
                camino.pop()
                visitados.remove(v)
        if not hubo_vecino:                         # caso base 2: callejón sin salida
            rutas.append(list(camino))

    dfs(0)
    return rutas, llamadas

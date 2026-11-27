"""Percepción: cono de visión con línea de visión (Bresenham) y percepción de ruido."""
from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from core.graph import VECTORES, Grafo, Mapa

Pos = Tuple[int, int]


def bresenham(a: Pos, b: Pos) -> List[Pos]:
    """Casillas de la línea recta de a a b (ambas incluidas)."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err, pts = dx + dy, []
    while True:
        pts.append((x0, y0))
        if (x0, y0) == (x1, y1):
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def hay_linea_de_vision(mapa: Mapa, a: Pos, b: Pos) -> bool:
    """True si ninguna casilla INTERMEDIA bloquea la vista (pared o puerta cerrada)."""
    return not any(mapa.bloquea_vision(p) for p in bresenham(a, b)[1:-1])


def en_cono(origen: Pos, direccion: str, destino: Pos, radio: float, angulo: float) -> bool:
    """¿destino está dentro del sector circular (radio, ángulo total en grados) orientado a `direccion`?"""
    vx, vy = destino[0] - origen[0], destino[1] - origen[1]
    d = math.hypot(vx, vy)
    if d == 0:
        return True
    if d > radio:
        return False
    dx, dy = VECTORES[direccion]
    cos = (vx * dx + vy * dy) / d
    return cos >= math.cos(math.radians(angulo / 2)) - 1e-9


def ve(mapa: Mapa, origen: Pos, direccion: str, radio: float, angulo: float, objetivo: Pos) -> bool:
    """Visión: dentro del cono y con línea de visión libre."""
    return en_cono(origen, direccion, objetivo, radio, angulo) and \
        hay_linea_de_vision(mapa, origen, objetivo)


def celdas_visibles(mapa: Mapa, origen: Pos, direccion: str, radio: float, angulo: float) -> List[Pos]:
    """Todas las casillas no-pared dentro del cono con línea de visión (para dibujar el cono)."""
    r = int(radio)
    out = []
    for y in range(origen[1] - r, origen[1] + r + 1):
        for x in range(origen[0] - r, origen[0] + r + 1):
            p = (x, y)
            if mapa.en_rango(p) and not mapa.es_pared(p) and \
                    en_cono(origen, direccion, p, radio, angulo) and hay_linea_de_vision(mapa, origen, p):
                out.append(p)
    return out


def oye_ruido(oyente: Pos, fuente: Pos, radio_audicion: float) -> bool:
    """El ruido se oye si la fuente está dentro del radio de audición (distancia euclídea)."""
    return math.hypot(oyente[0] - fuente[0], oyente[1] - fuente[1]) <= radio_audicion


def estimar_posicion_ruido(grafo: Grafo, fuente: Pos, rng: random.Random, error: int = 2) -> Pos:
    """Posición ESTIMADA (imprecisa) del ruido: la real desplazada hasta `error` casillas,
    ajustada a la casilla transitable más cercana."""
    obj = (fuente[0] + rng.randint(-error, error), fuente[1] + rng.randint(-error, error))
    if obj in grafo.ady:
        return obj
    return min(grafo.ady, key=lambda p: (abs(p[0] - obj[0]) + abs(p[1] - obj[1]), p))

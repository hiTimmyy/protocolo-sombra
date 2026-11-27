"""Generación de mapas por semilla: salas + pasillos, con verificación de conectividad."""
from __future__ import annotations

import random
from typing import Optional

from core.graph import ALFOMBRA, PISO, Mapa, construir_grafo
from core.pathfinding import dijkstra


def _intentar(rng: random.Random, ancho: int, alto: int, n_salas: int) -> Optional[Mapa]:
    m = Mapa(ancho, alto)
    # 1) Colocar salas sin solaparse (con 1 casilla de pared entre ellas).
    for _ in range(n_salas * 40):
        if len(m.salas) >= n_salas:
            break
        w, h = rng.randint(4, 8), rng.randint(3, 6)
        if ancho - w - 3 < 2 or alto - h - 3 < 1:
            continue
        x, y = rng.randint(2, ancho - w - 2), rng.randint(1, alto - h - 2)
        if all(x > sx + sw + 1 or sx > x + w + 1 or y > sy + sh + 1 or sy > y + h + 1
               for sx, sy, sw, sh in m.salas):
            m.salas.append((x, y, w, h))
    if len(m.salas) < 4:
        return None
    m.salas.sort()                       # de izquierda a derecha: sala 0 = sala de entrada
    en_sala = set()
    for i, (x, y, w, h) in enumerate(m.salas):
        tipo = ALFOMBRA if rng.random() < 0.35 else PISO
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                m.tipos[yy][xx] = tipo
                en_sala.add((xx, yy))
    # 2) Pasillos en L entre salas consecutivas + algunos extra (crean rutas alternativas).
    pares = [(i, i + 1) for i in range(len(m.salas) - 1)]
    for _ in range(max(2, len(m.salas) // 3)):
        a, b = rng.sample(range(len(m.salas)), 2)
        pares.append((a, b))
    pasillo = set()

    def cavar(p):
        if m.tipos[p[1]][p[0]] != PISO and p not in en_sala:
            m.tipos[p[1]][p[0]] = PISO
        if p not in en_sala:
            pasillo.add(p)

    for a, b in pares:
        (x1, y1), (x2, y2) = m.centro_sala(a), m.centro_sala(b)
        if rng.random() < 0.5:
            cam = [(x, y1) for x in range(min(x1, x2), max(x1, x2) + 1)] + \
                  [(x2, y) for y in range(min(y1, y2), max(y1, y2) + 1)]
        else:
            cam = [(x1, y) for y in range(min(y1, y2), max(y1, y2) + 1)] + \
                  [(x, y2) for x in range(min(x1, x2), max(x1, x2) + 1)]
        for p in cam:
            cavar(p)
    # 3) Entrada por el lado izquierdo, alineada con el centro de la sala 0.
    ex, ey = m.centro_sala(0)
    for x in range(0, m.salas[0][0]):
        cavar((x, ey))
    m.entrada = (0, ey)
    # 4) Puertas: casillas de pasillo pegadas a una sala que forman un paso estrecho.
    pared = m.es_pared
    for (x, y) in sorted(pasillo):
        if (x, y) == m.entrada:
            continue
        junto_a_sala = any((x + dx, y + dy) in en_sala for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        estrecho = (pared((x, y - 1)) and pared((x, y + 1))) or (pared((x - 1, y)) and pared((x + 1, y)))
        if junto_a_sala and estrecho and rng.random() < 0.7:
            m.agregar_puerta((x, y))
    m.waypoints = [m.centro_sala(i) for i in range(len(m.salas))]
    return m


def _conectado(m: Mapa) -> bool:
    g = construir_grafo(m)
    alc = g.alcanzables(m.entrada)
    return all(c in alc for c in m.waypoints)


def generar_mapa(seed: int, ancho: int = 30, alto: int = 20, n_salas: Optional[int] = None) -> Mapa:
    """Mapa conexo generado por semilla (misma semilla -> mismo mapa)."""
    n_salas = n_salas or max(5, ancho * alto // 90)
    rng = random.Random(seed)
    for _ in range(200):
        m = _intentar(rng, ancho, alto, n_salas)
        if m is not None and _conectado(m):
            return m
    raise RuntimeError(f"No se pudo generar un mapa conexo (seed={seed})")


def generar_nivel(seed: int, ancho: int = 30, alto: int = 20) -> Mapa:
    """Mapa jugable: entrada, terminal, extracción y una puerta clave tal que, al
    bloquearla, siga habiendo ruta terminal -> extracción (escena "doble ruta")."""
    for k in range(500):
        m = generar_mapa(seed + 7919 * k, ancho, alto)
        n = len(m.salas)
        m.terminal, m.extraccion = m.waypoints[n // 2], m.waypoints[n - 1]
        g = construir_grafo(m)
        ruta = dijkstra(g, m.terminal, m.extraccion).ruta
        for p in ruta:
            puerta = m.puerta_en(p)
            if puerta is None:
                continue
            puerta.estado = "bloqueada"
            alterna = dijkstra(construir_grafo(m), m.terminal, m.extraccion).ruta
            puerta.estado = "cerrada"
            if alterna:
                m.puerta_clave = puerta.id
                return m
    raise RuntimeError(f"No se pudo generar un nivel con doble ruta (seed={seed})")

"""Cuadrícula (Mapa) y su conversión a grafo (Grafo).

Vértices: casillas que no son pared. Aristas: dirigidas, a las 4 vecinas
(arriba, abajo, izquierda, derecha). Costo de una arista = costo de la casilla
de destino (piso/puerta = 1, alfombra = 2). Una puerta bloqueada no tiene
aristas de ENTRADA (nadie puede entrar), pero conserva las de salida para que
quien esté encima pueda salir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Pos = Tuple[int, int]
VECTORES = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}
PARED, PISO, ALFOMBRA = "#", ".", ","
COSTO_TERRENO = {PISO: 1, ALFOMBRA: 2}


@dataclass
class Puerta:
    id: int
    pos: Pos
    estado: str = "cerrada"   # "abierta" | "cerrada" | "bloqueada"


class Mapa:
    """Cuadrícula de terreno + puertas + puntos especiales."""

    def __init__(self, ancho: int, alto: int):
        self.ancho, self.alto = ancho, alto
        self.tipos: List[List[str]] = [[PARED] * ancho for _ in range(alto)]
        self.puertas: Dict[int, Puerta] = {}
        self._puerta_en: Dict[Pos, int] = {}
        self.entrada: Optional[Pos] = None
        self.terminal: Optional[Pos] = None
        self.extraccion: Optional[Pos] = None
        self.puerta_clave: Optional[int] = None       # puerta que se bloquea tras el hackeo
        self.salas: List[Tuple[int, int, int, int]] = []  # (x, y, ancho, alto)
        self.waypoints: List[Pos] = []                # puntos de patrulla (centros de sala)

    # --- consultas de casillas ---
    def en_rango(self, p: Pos) -> bool:
        return 0 <= p[0] < self.ancho and 0 <= p[1] < self.alto

    def tipo(self, p: Pos) -> str:
        return self.tipos[p[1]][p[0]] if self.en_rango(p) else PARED

    def puerta_en(self, p: Pos) -> Optional[Puerta]:
        i = self._puerta_en.get(p)
        return self.puertas[i] if i is not None else None

    def es_pared(self, p: Pos) -> bool:
        return self.tipo(p) == PARED

    def transitable(self, p: Pos) -> bool:
        """Se puede entrar: no es pared ni puerta bloqueada."""
        if self.es_pared(p):
            return False
        d = self.puerta_en(p)
        return d is None or d.estado != "bloqueada"

    def bloquea_vision(self, p: Pos) -> bool:
        """Paredes y puertas cerradas/bloqueadas impiden ver."""
        if self.es_pared(p):
            return True
        d = self.puerta_en(p)
        return d is not None and d.estado != "abierta"

    def costo(self, p: Pos) -> int:
        return COSTO_TERRENO.get(self.tipo(p), 0)

    def agregar_puerta(self, p: Pos, estado: str = "cerrada") -> int:
        i = len(self.puertas)
        self.puertas[i] = Puerta(i, p, estado)
        self._puerta_en[p] = i
        return i

    def centro_sala(self, i: int) -> Pos:
        x, y, w, h = self.salas[i]
        return (x + w // 2, y + h // 2)

    @staticmethod
    def desde_ascii(lineas: List[str]) -> "Mapa":
        """Crea un mapa desde texto (útil en pruebas). '#' pared, '.' piso, ',' alfombra,
        'D' puerta cerrada, 'N' entrada, 'T' terminal, 'X' extracción."""
        m = Mapa(len(lineas[0]), len(lineas))
        for y, fila in enumerate(lineas):
            for x, c in enumerate(fila):
                p = (x, y)
                if c == "#":
                    continue
                m.tipos[y][x] = ALFOMBRA if c == "," else PISO
                if c == "D":
                    m.agregar_puerta(p)
                elif c == "N":
                    m.entrada = p
                elif c == "T":
                    m.terminal = p
                elif c == "X":
                    m.extraccion = p
        return m


@dataclass
class Grafo:
    """Lista de adyacencia: ady[v] = [(vecino, costo), ...]. Un vértice es una casilla (x, y)."""
    ady: Dict[Pos, List[Tuple[Pos, int]]] = field(default_factory=dict)

    @property
    def V(self) -> int:
        return len(self.ady)

    @property
    def E(self) -> int:
        return sum(len(a) for a in self.ady.values())

    def alcanzables(self, origen: Pos) -> set:
        """Conjunto de vértices alcanzables desde `origen` (recorrido en anchura)."""
        vistos, cola = {origen}, [origen]
        while cola:
            u = cola.pop()
            for v, _ in self.ady.get(u, ()):
                if v not in vistos:
                    vistos.add(v)
                    cola.append(v)
        return vistos


def construir_grafo(mapa: Mapa) -> Grafo:
    """Convierte la cuadrícula en grafo. Se reconstruye cuando cambia una puerta."""
    g = Grafo()
    for y in range(mapa.alto):
        for x in range(mapa.ancho):
            if not mapa.es_pared((x, y)):
                g.ady[(x, y)] = []
    for (x, y), lista in g.ady.items():
        for dx, dy in VECTORES.values():
            v = (x + dx, y + dy)
            if v in g.ady and mapa.transitable(v):
                lista.append((v, mapa.costo(v)))
    return g

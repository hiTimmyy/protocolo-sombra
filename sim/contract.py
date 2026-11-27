"""Contrato entre la simulación y la UI.

La UI SOLO debe usar `sim.step(accion)`, `sim.snapshot()`, `sim.falsa_alarma(pos)`
y `sim.bloquear_puerta(id)`. Todo lo que la UI necesita ver viene en `Snapshot`.
Este módulo no importa pygame. Coordenadas: (x, y) con (0, 0) arriba-izquierda.
Tiempo: 1 tick = 1/ticks_por_segundo s. Nox camina 1 casilla cada 2 ticks y corre
1 casilla por tick; los guardias se mueven 1 casilla cada 2-3 ticks (la UI interpola).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Pos = Tuple[int, int]

# Valores posibles de campos de texto
DIRECCIONES = ("arriba", "abajo", "izquierda", "derecha")
ESTADOS_GUARDIA = ("PATRULLA", "INVESTIGAR", "BUSCAR", "ALERTA", "VOLVER_A_PATRULLA")
ESTADOS_PUERTA = ("abierta", "cerrada", "bloqueada")
NIVELES_ALERTA = ("verde", "amarilla", "roja")
RESULTADOS = ("jugando", "gano", "perdio")


@dataclass
class Accion:
    """Entrada de Nox para un tick (se pasa a `sim.step`)."""
    mover: Optional[str] = None   # una de DIRECCIONES o None (quieta)
    correr: bool = False          # True = 1 casilla/tick pero genera ruido
    interactuar: bool = False     # True = mantener E (hackear si está junto a la terminal)
    senuelo: bool = False         # True = lanzar un señuelo de ruido (tecla Q, cantidad limitada)


@dataclass
class PuertaSnap:
    id: int
    pos: Pos
    estado: str                   # "abierta" | "cerrada" | "bloqueada"
    es_clave: bool = False        # True = la puerta que se bloquea sola tras el hackeo


@dataclass
class MapaSnap:
    ancho: int
    alto: int
    # tiles[y][x] es un carácter: '#' pared, '.' piso, ',' alfombra (costo 2),
    # 'D' puerta (ver `puertas` para su estado), 'T' terminal, 'X' extracción.
    tiles: List[str]
    costos: List[List[int]]       # costos[y][x]: costo de entrar a la casilla (0 en paredes = intransitable)
    puertas: List[PuertaSnap]
    entrada: Pos                  # casilla de entrada de Nox (borde lateral)
    terminal: Pos
    extraccion: Pos


@dataclass
class NoxSnap:
    pos: Pos
    direccion: str
    corriendo: bool
    hackeo_progreso: float        # 0.0 - 1.0 (barra de progreso)
    tiene_archivo: bool           # True tras completar el hackeo
    senuelos: int = 0             # señuelos de ruido que le quedan


@dataclass
class GuardiaSnap:
    id: int
    pos: Pos
    direccion: str
    estado: str                   # ver ESTADOS_GUARDIA
    burbuja: str                  # "!" (ve a Nox), "?" (investiga/busca) o "" (nada)
    objetivo: Optional[Pos]       # destino actual de la ruta
    ruta: List[Pos]               # casillas pendientes hasta el objetivo
    algoritmo: str                # "Dijkstra" | "A*"
    heuristica: str               # "Manhattan" | "ninguna"
    costo: float                  # costo de la última ruta planificada
    nodos_expandidos: int         # nodos expandidos en la última búsqueda
    tiempo_busqueda_s: float      # tiempo de la última búsqueda (segundos)
    percepcion: str               # texto corto: "ve a Nox", "oye ruido", "mensaje de camara_0", "nada"
    cono: List[Pos]               # casillas dentro del cono de visión (ya con línea de visión)
    evidencias: List[Tuple[Pos, int]] = field(default_factory=list)  # (pos, tick) vigentes en memoria
    replanificaciones: int = 0


@dataclass
class CamaraSnap:
    id: int
    pos: Pos
    direccion: str
    celdas_vistas: List[Pos]
    detecta: bool                 # True si ve a Nox en este tick


@dataclass
class Snapshot:
    tick: int
    ticks_por_segundo: int
    mapa: MapaSnap
    nox: NoxSnap
    guardias: List[GuardiaSnap]
    camaras: List[CamaraSnap]
    alerta: str                   # "verde" | "amarilla" | "roja"
    log: List[str]                # últimos mensajes del bus / replaneos / cambios de estado
    tiempo_restante_s: float
    resultado: str                # "jugando" | "gano" | "perdio"

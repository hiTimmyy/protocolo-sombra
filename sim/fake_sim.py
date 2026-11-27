"""Simulación falsa para desarrollar la UI sin la lógica real.

Misma interfaz que `Simulation`: step(accion), snapshot(), falsa_alarma(pos),
bloquear_puerta(id). Devuelve snapshots de ejemplo (mapa pequeño, 2 guardias,
una cámara, burbujas "!" y "?"). No usa pygame ni el resto de la lógica.
"""
from __future__ import annotations

from sim.contract import (Accion, CamaraSnap, GuardiaSnap, MapaSnap, NoxSnap,
                          PuertaSnap, Snapshot)

_MAPA = [
    "####################",
    "#......#...........#",
    "#..,,..D...,,,.....#",
    "#..,,..#...,,,..T..#",
    "#......#...........#",
    "#####D######D#######",
    "#..........#.......#",
    "#..,,,.....D.....X.#",
    "####################",
]
_VEC = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}


class FakeSimulation:
    def __init__(self, seed: int = 0, config=None):
        self.tick = 0
        self.alto, self.ancho = len(_MAPA), len(_MAPA[0])
        self.nox = [1, 1]
        self.dir = "derecha"
        self.corriendo = False
        self.hack = 0.0
        self.archivo = False
        self.estados_puerta = {}
        self.puertas = []
        for y, fila in enumerate(_MAPA):
            for x, c in enumerate(fila):
                if c == "D":
                    self.puertas.append((len(self.puertas), (x, y)))
                    self.estados_puerta[len(self.puertas) - 1] = "cerrada"
        self.log = ["[t0] FakeSimulation iniciada"]
        self.resultado = "jugando"
        self.forzar_investigar = 0   # ticks restantes del estado INVESTIGAR por falsa alarma
        self.objetivo_alarma = (14, 4)

    # --- interfaz igual a Simulation ---
    def step(self, accion: Accion | None = None) -> Snapshot:
        a = accion or Accion()
        if self.resultado != "jugando":
            return self.snapshot()
        self.tick += 1
        self.forzar_investigar = max(0, self.forzar_investigar - 1)
        cerca = abs(self.nox[0] - 16) + abs(self.nox[1] - 3) <= 1
        if a.interactuar and cerca and not self.archivo:
            self.hack = min(1.0, self.hack + 1 / 30)
            if self.hack >= 1.0:
                self.archivo, self.hack = True, 0.0
                self.log.append(f"[t{self.tick}] ALARMA global (hackeo completo)")
        else:
            self.hack = 0.0
        self.corriendo = a.correr and a.mover is not None
        if a.mover and not a.interactuar and (self.tick % 2 == 0 or a.correr):
            self.dir = a.mover
            dx, dy = _VEC[a.mover]
            nx, ny = self.nox[0] + dx, self.nox[1] + dy
            if _MAPA[ny][nx] != "#" and not self._bloqueada(nx, ny):
                self.nox = [nx, ny]
        if self.archivo and tuple(self.nox) == (17, 7):
            self.resultado = "gano"
        if self.tick >= 1500:
            self.resultado = "perdio"
        return self.snapshot()

    def falsa_alarma(self, pos) -> None:
        self.objetivo_alarma = tuple(pos)
        self.forzar_investigar = 60
        self.log.append(f"[t{self.tick}] FALSA_ALARMA en {tuple(pos)}")

    def bloquear_puerta(self, id: int) -> None:
        if id in self.estados_puerta:
            self.estados_puerta[id] = "bloqueada"
            self.log.append(f"[t{self.tick}] PUERTA {id} bloqueada; guardias replanifican")

    def _bloqueada(self, x, y) -> bool:
        return any(p == (x, y) and self.estados_puerta[i] == "bloqueada" for i, p in self.puertas)

    # --- snapshot de ejemplo ---
    def snapshot(self) -> Snapshot:
        tiles = [fila.replace("D", "D") for fila in _MAPA]
        costos = [[0 if c == "#" else (2 if c == "," else 1) for c in fila] for fila in _MAPA]
        puertas = [PuertaSnap(i, p, self.estados_puerta[i], es_clave=(i == 1)) for i, p in self.puertas]
        mapa = MapaSnap(self.ancho, self.alto, tiles, costos, puertas, (0, 1), (16, 3), (17, 7))
        # Guardia 0 patrulla de ida y vuelta por la fila 6; guardia 1 cicla estados.
        fase = (self.tick // 2) % 16
        g0x = 1 + (fase if fase < 9 else 16 - fase)
        g0 = GuardiaSnap(0, (g0x, 6), "derecha" if fase < 9 else "izquierda", "PATRULLA", "",
                         (9, 6), [(x, 6) for x in range(g0x + 1, 10)], "A*", "Manhattan",
                         9.0, 31, 0.0002, "nada", [(g0x + i, 6) for i in range(1, 4)])
        g1_estado = "INVESTIGAR" if self.forzar_investigar else ("ALERTA" if (self.tick // 40) % 2 else "PATRULLA")
        burbuja = {"INVESTIGAR": "?", "ALERTA": "!"}.get(g1_estado, "")
        g1 = GuardiaSnap(1, (12, 2), "izquierda", g1_estado, burbuja,
                         self.objetivo_alarma if g1_estado == "INVESTIGAR" else None, [],
                         "Dijkstra", "ninguna", 12.0, 88, 0.0007,
                         "ve a Nox" if g1_estado == "ALERTA" else "nada",
                         [(11, 2), (10, 2), (11, 3), (10, 3)],
                         [(self.objetivo_alarma, self.tick)] if self.forzar_investigar else [])
        cam = CamaraSnap(0, (14, 1), "abajo", [(14, 2), (14, 3), (13, 3), (15, 3)], False)
        nivel = "roja" if self.archivo or g1_estado == "ALERTA" else ("amarilla" if self.forzar_investigar else "verde")
        nox = NoxSnap(tuple(self.nox), self.dir, self.corriendo, self.hack, self.archivo)
        return Snapshot(self.tick, 10, mapa, nox, [g0, g1], [cam], nivel, self.log[-30:],
                        max(0.0, (1500 - self.tick) / 10), self.resultado)

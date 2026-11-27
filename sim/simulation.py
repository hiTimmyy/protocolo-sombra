"""Simulación del juego (sin pygame). Interfaz para la UI: step, snapshot, falsa_alarma, bloquear_puerta.

Un tick = 1/ticks_por_segundo s. Nox camina 1 casilla cada 2 ticks y corre 1 por tick
(el correr genera ruido que oyen los guardias dentro de `radio_ruido`).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from agents.bus import Bus, Mensaje
from agents.camara import Camara
from agents.guard import ALERTA, BUSCAR, INVESTIGAR, Entorno, Guardia
from agents.perception import celdas_visibles
from core.graph import Mapa, construir_grafo
from core.pathfinding import manhattan
from sim.contract import (Accion, CamaraSnap, GuardiaSnap, MapaSnap, NoxSnap,
                          PuertaSnap, Snapshot)
from sim.mapgen import generar_nivel

Pos = Tuple[int, int]
_VEC = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}


@dataclass
class Config:
    ancho: int = 30
    alto: int = 20
    n_guardias: int = 3              # 2 a 4
    algoritmo: str = "astar"         # "astar" | "dijkstra"
    cobertura: str = "dinamica"      # "dinamica" (reacciona a ruido y mensajes) | "fija"
    ticks_por_segundo: int = 10
    tiempo_limite_s: float = 150.0
    hackeo_s: float = 3.0
    ttl_evidencia: int = 120         # ticks que dura una evidencia en memoria
    radio_vision: float = 6
    angulo_vision: float = 90
    radio_ruido: float = 7           # radio de audición del ruido de Nox al correr
    prof_busqueda: int = 6
    alarma_ticks: int = 100          # duración de la alerta roja tras el hackeo
    guardias_inicio: Optional[List[Pos]] = None   # solo pruebas
    camaras_inicio: Optional[List[Tuple[Pos, str]]] = None  # solo pruebas


@dataclass
class NoxEstado:
    pos: Pos
    dir: str = "derecha"
    corriendo: bool = False
    hack: float = 0.0
    tiene_archivo: bool = False
    cooldown: int = 0


def asignar_patrullas(grafo, posiciones: List[Pos], waypoints: List[Pos]) -> List[List[Pos]]:
    """Reparte waypoints entre guardias: cada waypoint va al guardia que lo ALCANZA con menos
    carga. Los inalcanzables (p. ej. tras bloquear una puerta) quedan sin asignar."""
    alcance = [grafo.alcanzables(p) for p in posiciones]
    listas: List[List[Pos]] = [[] for _ in posiciones]
    for w in waypoints:
        cand = [i for i in range(len(posiciones)) if w in alcance[i]]
        if cand:
            listas[min(cand, key=lambda i: (len(listas[i]), i))].append(w)
    return [sorted(l) for l in listas]


class Simulation:
    def __init__(self, seed: int = 0, config: Optional[Config] = None, mapa: Optional[Mapa] = None):
        self.seed, self.cfg = seed, config or Config()
        self.rng = random.Random(seed)
        self.mapa = mapa or generar_nivel(seed, self.cfg.ancho, self.cfg.alto)
        self.version_grafo = 0
        self.grafo = construir_grafo(self.mapa)
        self.bus = Bus()
        self.tick = 0
        self.resultado = "jugando"
        self.alarma_hasta = -1
        self.limite_ticks = int(self.cfg.tiempo_limite_s * self.cfg.ticks_por_segundo)
        self.nox = NoxEstado(self.mapa.entrada)
        self._crear_agentes()

    # ---------- creación ----------
    def _crear_agentes(self) -> None:
        m, c = self.mapa, self.cfg
        if c.guardias_inicio is not None:
            inicios = list(c.guardias_inicio)
        else:
            n = len(m.salas)
            # Guardias en las salas alejadas de la entrada (salas 2..n-1), una por sala si es posible.
            inicios = [m.waypoints[2 + i % (n - 2)] for i in range(c.n_guardias)]
        wps = asignar_patrullas(self.grafo, inicios, m.waypoints)
        self.guardias = [Guardia(i, p, wps[i], self.bus, c.algoritmo, c.ttl_evidencia, c.radio_vision,
                                 c.angulo_vision, c.cobertura == "dinamica", c.prof_busqueda)
                         for i, p in enumerate(inicios)]
        if c.camaras_inicio is not None:
            cams = c.camaras_inicio
        else:   # cámaras en el centro del muro superior de 2 salas (no la de entrada ni la de la terminal)
            n = len(m.salas)
            libres = [i for i in range(1, n) if m.waypoints[i] not in (m.terminal, m.extraccion)] or [1]
            cams = []
            for i in libres[:1] + libres[-1:]:
                x, y, w, h = m.salas[i]
                cams.append(((x + w // 2, y), "abajo"))
        self.camaras = [Camara(i, p, d, self.bus) for i, (p, d) in enumerate(cams[:2])]

    # ---------- eventos inyectables ----------
    def falsa_alarma(self, pos: Pos) -> None:
        """Un aviso falso en `pos`: el guardia más cercano lo investiga."""
        pos = tuple(pos)
        cerca = min(self.guardias, key=lambda g: manhattan(g.pos, pos))
        self.bus.publicar(Mensaje(self.tick, "sistema", "FALSA_ALARMA", pos, destino=cerca.nombre))

    def bloquear_puerta(self, id: int) -> None:
        """Bloquea la puerta: se reconstruye el grafo, los guardias replanifican y las patrullas se reorganizan."""
        puerta = self.mapa.puertas.get(id)
        if puerta is None or puerta.estado == "bloqueada":
            return
        puerta.estado = "bloqueada"
        self.version_grafo += 1
        self.grafo = construir_grafo(self.mapa)
        self.bus.publicar(Mensaje(self.tick, "sistema", "PUERTA_BLOQUEADA", puerta.pos))
        self._reorganizar_patrullas()

    def _reorganizar_patrullas(self) -> None:
        listas = asignar_patrullas(self.grafo, [g.pos for g in self.guardias], self.mapa.waypoints)
        for g, wps in zip(self.guardias, listas):
            g.asignar_waypoints(wps)
        self.bus.registrar(self.tick, "Patrullas reorganizadas: " +
                           ", ".join(f"{g.nombre}={len(g.waypoints)} puntos" for g in self.guardias))

    # ---------- bucle ----------
    def step(self, accion: Optional[Accion] = None) -> Snapshot:
        if self.resultado != "jugando":
            return self.snapshot()
        a = accion or Accion()
        self.tick += 1
        hace_ruido = self._mover_nox(a)
        self._actualizar_puertas()
        env = Entorno(self.tick, self.mapa, self.grafo, self.version_grafo, self.nox.pos,
                      hace_ruido, self.cfg.radio_ruido, self.rng)
        for c in self.camaras:
            c.paso(env)
        for g in self.guardias:
            g.paso(env)
        self._actualizar_puertas()
        if self.nox.tiene_archivo and self.nox.pos == self.mapa.extraccion:
            self.resultado = "gano"
        elif any(manhattan(g.pos, self.nox.pos) <= 1 for g in self.guardias) or self.tick >= self.limite_ticks:
            self.resultado = "perdio"
        return self.snapshot()

    def _mover_nox(self, a: Accion) -> bool:
        n, c = self.nox, self.cfg
        puede = n.cooldown == 0
        n.cooldown = max(0, n.cooldown - 1)
        n.corriendo = False
        if a.interactuar:                       # hackear: debe estar junto a la terminal
            if not n.tiene_archivo and manhattan(n.pos, self.mapa.terminal) <= 1:
                n.hack += 1.0 / (c.hackeo_s * c.ticks_por_segundo)
                if n.hack >= 1.0:
                    self._completar_hackeo()
            else:
                n.hack = 0.0
            return False
        n.hack = 0.0                            # moverse interrumpe el hackeo
        if a.mover:
            n.dir = a.mover
            n.corriendo = a.correr
            dest = (n.pos[0] + _VEC[a.mover][0], n.pos[1] + _VEC[a.mover][1])
            if puede and self.mapa.transitable(dest):
                n.pos = dest
                n.cooldown = 0 if a.correr else 1
                return a.correr                 # correr hace ruido
        return False

    def _completar_hackeo(self) -> None:
        self.nox.tiene_archivo, self.nox.hack = True, 0.0
        self.alarma_hasta = self.tick + self.cfg.alarma_ticks
        self.bus.registrar(self.tick, "Terminal hackeada: ALERTA GLOBAL")
        self.bus.publicar(Mensaje(self.tick, "sistema", "ALARMA", self.mapa.terminal))
        if self.mapa.puerta_clave is not None:
            self.bloquear_puerta(self.mapa.puerta_clave)

    def _actualizar_puertas(self) -> None:
        """Una puerta se abre mientras alguien está sobre ella y se cierra después."""
        ocupadas = {self.nox.pos} | {g.pos for g in self.guardias}
        for p in self.mapa.puertas.values():
            if p.estado != "bloqueada":
                p.estado = "abierta" if p.pos in ocupadas else "cerrada"

    # ---------- snapshot ----------
    def _alerta(self) -> str:
        if self.tick <= self.alarma_hasta or any(g.estado == ALERTA for g in self.guardias):
            return "roja"
        if any(g.estado in (INVESTIGAR, BUSCAR) for g in self.guardias) or any(c.detecta for c in self.camaras):
            return "amarilla"
        return "verde"

    def snapshot(self) -> Snapshot:
        m = self.mapa
        tiles = []
        for y in range(m.alto):
            fila = []
            for x in range(m.ancho):
                p = (x, y)
                fila.append("D" if m.puerta_en(p) else "T" if p == m.terminal else
                            "X" if p == m.extraccion else m.tipos[y][x])
            tiles.append("".join(fila))
        costos = [[m.costo((x, y)) for x in range(m.ancho)] for y in range(m.alto)]
        puertas = [PuertaSnap(p.id, p.pos, p.estado, p.id == m.puerta_clave) for p in m.puertas.values()]
        mapa = MapaSnap(m.ancho, m.alto, tiles, costos, puertas, m.entrada, m.terminal, m.extraccion)
        n = self.nox
        nox = NoxSnap(n.pos, n.dir, n.corriendo, min(1.0, n.hack), n.tiene_archivo)
        gs = [GuardiaSnap(g.id, g.pos, g.dir, g.estado,
                          "!" if g.estado == ALERTA else "?" if g.estado in (INVESTIGAR, BUSCAR) else "",
                          g.objetivo, list(g.ruta), "A*" if g.algoritmo == "astar" else "Dijkstra",
                          g.heuristica, g.costo, g.nodos, g.tiempo_busqueda, g.percepcion_txt,
                          list(g.cono), [(e.pos, e.tick) for e in g.memoria.vigentes(self.tick)],
                          g.replanificaciones) for g in self.guardias]
        cs = [CamaraSnap(c.id, c.pos, c.direccion, list(c.celdas_vistas), c.detecta) for c in self.camaras]
        tps = self.cfg.ticks_por_segundo
        return Snapshot(self.tick, tps, mapa, nox, gs, cs, self._alerta(), self.bus.log[-40:],
                        max(0.0, (self.limite_ticks - self.tick) / tps), self.resultado)

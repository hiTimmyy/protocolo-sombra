"""Guardia autónomo: máquina de estados PATRULLA -> INVESTIGAR -> BUSCAR -> ALERTA -> VOLVER_A_PATRULLA.

Ciclo de cada tick (`paso`): percibir -> memorizar -> decidir -> planificar -> ejecutar -> evaluar.
`decidir` fija estado y objetivo (qué hacer); `planificar` calcula la ruta (cómo) con
Dijkstra o A*, y la REPLANIFICA si cambió el grafo (puerta) o el objetivo.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from agents import perception
from agents.bus import Bus, Mensaje
from agents.memory import Memoria
from core.graph import Grafo, Mapa
from core.pathfinding import a_estrella, dijkstra, manhattan
from core.recursion import rutas_dfs

Pos = Tuple[int, int]
PATRULLA, INVESTIGAR, BUSCAR, ALERTA, VOLVER = "PATRULLA", "INVESTIGAR", "BUSCAR", "ALERTA", "VOLVER_A_PATRULLA"
_DIR = {(0, -1): "arriba", (0, 1): "abajo", (-1, 0): "izquierda", (1, 0): "derecha"}


@dataclass
class Entorno:
    """Lo que la simulación le entrega a agentes en cada tick."""
    tick: int
    mapa: Mapa
    grafo: Grafo
    version_grafo: int          # cambia cuando se bloquea una puerta
    nox_pos: Pos
    nox_hace_ruido: bool        # Nox corrió en este tick
    radio_ruido: float          # radio de audición
    rng: random.Random


@dataclass
class Percepcion:
    ve_nox: bool = False
    ruido: Optional[Pos] = None
    avisos: List[Mensaje] = field(default_factory=list)


class Guardia:
    def __init__(self, id: int, pos: Pos, waypoints: List[Pos], bus: Bus, algoritmo: str = "astar",
                 ttl: int = 120, radio_vision: float = 6, angulo_vision: float = 90,
                 reactivo: bool = True, prof_busqueda: int = 6, prof_patrulla: int = 8):
        self.id, self.nombre = id, f"guardia_{id}"
        self.pos, self.dir = pos, "derecha"
        self.bus, self.algoritmo = bus, algoritmo
        self.memoria = Memoria(ttl)
        self.radio_vision, self.angulo_vision = radio_vision, angulo_vision
        self.reactivo = reactivo            # False = cobertura fija: ignora ruido y mensajes
        self.prof_busqueda = prof_busqueda
        self.prof_patrulla = prof_patrulla  # profundidad del DFS que explora tramos de patrulla
        self.visitas = {}                   # casilla -> último tick en que este guardia la pisó
        self.tramos_dfs = 0                 # cuántos tramos de patrulla eligió con DFS
        self._en_tramo = False              # True mientras recorre un tramo elegido por DFS
        self.estado = PATRULLA
        self.waypoints: List[Pos] = []
        self.wp_idx = 0
        self.objetivo: Optional[Pos] = None
        self.ruta: List[Pos] = []           # casillas pendientes (sin la actual)
        self.candidatos: List[Pos] = []     # puntos de búsqueda (salen del DFS limitado)
        self.cono: List[Pos] = []
        self.percepcion_txt = "nada"
        # estadísticas de la última búsqueda
        self.costo, self.nodos, self.tiempo_busqueda = 0.0, 0, 0.0
        self.replanificaciones = 0
        self.inbox: List[Mensaje] = []
        self._espera = 0
        self._replan = True
        self._version = -1
        self._tick_ev = -1                  # tick de la evidencia que se está atendiendo
        self._ultimo_aviso = -999
        self.asignar_waypoints(waypoints)
        bus.suscribir(self.nombre, self.inbox.append)

    # ---------- utilidades ----------
    @property
    def heuristica(self) -> str:
        return "Manhattan" if self.algoritmo == "astar" else "ninguna"

    @property
    def periodo(self) -> int:
        """Ticks por casilla: más rápido al perseguir/investigar."""
        return 2 if self.estado in (ALERTA, INVESTIGAR) else 3

    def asignar_waypoints(self, wps: List[Pos]) -> None:
        """(Re)asigna la ruta de patrulla; se usa al inicio y al reorganizar tras un bloqueo."""
        self.waypoints = list(wps)
        self.wp_idx = min(range(len(wps)), key=lambda i: manhattan(self.pos, wps[i])) if wps else 0
        if self.estado in (PATRULLA, VOLVER):
            self._fijar_objetivo(self.waypoints[self.wp_idx] if wps else None)

    def _fijar_objetivo(self, pos: Optional[Pos]) -> None:
        self._en_tramo = False
        if pos != self.objetivo:
            self.objetivo, self._replan = pos, True

    def _cambiar(self, estado: str, env: Entorno) -> None:
        if estado != self.estado:
            self.bus.registrar(env.tick, f"{self.nombre}: {self.estado} -> {estado}")
            self.estado = estado

    # ---------- ciclo principal ----------
    def paso(self, env: Entorno) -> None:
        p = self._percibir(env)
        self._memorizar(p, env)
        self._decidir(p, env)
        self._planificar(env)
        self._ejecutar(env)
        self._evaluar(env)

    def _percibir(self, env: Entorno) -> Percepcion:
        p = Percepcion()
        self.cono = perception.celdas_visibles(env.mapa, self.pos, self.dir, self.radio_vision, self.angulo_vision)
        p.ve_nox = env.nox_pos in self.cono
        if self.reactivo:
            if env.nox_hace_ruido and perception.oye_ruido(self.pos, env.nox_pos, env.radio_ruido):
                p.ruido = perception.estimar_posicion_ruido(env.grafo, env.nox_pos, env.rng)
            p.avisos = [m for m in self.inbox if m.pos is not None and m.tipo != "PUERTA_BLOQUEADA"]
        self.inbox.clear()
        self.percepcion_txt = "ve a Nox" if p.ve_nox else ("oye ruido" if p.ruido else
                              (f"mensaje de {p.avisos[-1].emisor}" if p.avisos else "nada"))
        return p

    def _memorizar(self, p: Percepcion, env: Entorno) -> None:
        if p.ve_nox:
            self.memoria.agregar(env.nox_pos, env.tick, "vista")
            if env.tick - self._ultimo_aviso >= 8:
                self._ultimo_aviso = env.tick
                self.bus.publicar(Mensaje(env.tick, self.nombre, "AVISTAMIENTO", env.nox_pos))
        if p.ruido:
            self.memoria.agregar(p.ruido, env.tick, "ruido")
            if env.tick - self._ultimo_aviso >= 8:
                self._ultimo_aviso = env.tick
                self.bus.publicar(Mensaje(env.tick, self.nombre, "RUIDO", p.ruido))
        for m in p.avisos:
            self.memoria.agregar(m.pos, m.tick, m.emisor)
        self.memoria.purgar(env.tick)       # la evidencia caducada se olvida

    def _decidir(self, p: Percepcion, env: Entorno) -> None:
        ev = self.memoria.mas_reciente(env.tick)
        if p.ve_nox:                                         # lo veo: perseguir
            self._cambiar(ALERTA, env)
            self._tick_ev = env.tick
            self._fijar_objetivo(env.nox_pos)
            return
        if self.estado == ALERTA:                            # lo perdí de vista
            self._cambiar(INVESTIGAR if ev else VOLVER, env)
            self._fijar_objetivo(ev.pos if ev else self._waypoint_cercano())
        elif ev and ev.tick > self._tick_ev:                 # evidencia nueva: investigar
            self._tick_ev = ev.tick
            self._cambiar(INVESTIGAR, env)
            self._fijar_objetivo(ev.pos)
        if self.estado == INVESTIGAR:
            if not ev:
                self._volver(env)
            elif self.pos == self.objetivo:                  # llegué: buscar alrededor
                self._cambiar(BUSCAR, env)
                self._generar_candidatos(env, self.pos)
        elif self.estado == BUSCAR:
            if not ev:                                       # la evidencia caducó: dejar de buscar
                self.candidatos.clear()
                self._volver(env)
            elif self.pos == self.objetivo or self.objetivo is None:
                self._siguiente_candidato(env)
        elif self.estado == VOLVER:
            if self.pos == self.objetivo:
                self._cambiar(PATRULLA, env)
                self._avanzar_waypoint()
        elif self.estado == PATRULLA and self.pos == self.objetivo:
            if self._en_tramo:
                self._avanzar_waypoint()            # terminó el tramo: siguiente waypoint
            else:
                self._explorar_tramo(env)           # llegó al waypoint: explorar su entorno

    def _volver(self, env: Entorno) -> None:
        self._cambiar(VOLVER, env)
        self._fijar_objetivo(self._waypoint_cercano())

    def _waypoint_cercano(self) -> Optional[Pos]:
        if not self.waypoints:
            return None
        self.wp_idx = min(range(len(self.waypoints)), key=lambda i: manhattan(self.pos, self.waypoints[i]))
        return self.waypoints[self.wp_idx]

    def _avanzar_waypoint(self) -> None:
        if self.waypoints:
            self.wp_idx = (self.wp_idx + 1) % len(self.waypoints)
            self._fijar_objetivo(self.waypoints[self.wp_idx])

    def _explorar_tramo(self, env: Entorno) -> None:
        """Patrulla con recursión: el DFS limitado enumera tramos de `prof_patrulla` pasos desde el
        waypoint y se elige el menos visitado recientemente (cubre zonas descuidadas)."""
        rutas, _ = rutas_dfs(env.grafo, self.pos, self.prof_patrulla, max_rutas=1500)
        mejor = max(rutas, key=lambda r: sum(min(env.tick - self.visitas.get(c, -300), 300) for c in r[1:]),
                    default=[self.pos])
        if len(mejor) < 2:
            self._avanzar_waypoint()
            return
        self.tramos_dfs += 1
        self.ruta, self.objetivo = mejor[1:], mejor[-1]
        self._replan, self._en_tramo = False, True

    def _generar_candidatos(self, env: Entorno, centro: Pos) -> None:
        """DFS recursivo limitado desde `centro`: los extremos de las rutas son puntos de búsqueda."""
        rutas, _ = rutas_dfs(env.grafo, centro, self.prof_busqueda, max_rutas=1500)
        fines = sorted({r[-1] for r in rutas} - {self.pos})
        env.rng.shuffle(fines)
        self.candidatos = sorted(fines[:4], key=lambda c: manhattan(self.pos, c))
        self._siguiente_candidato(env)

    def _siguiente_candidato(self, env: Entorno) -> None:
        if not self.candidatos:
            self._generar_candidatos(env, self.pos)
            return
        self._fijar_objetivo(self.candidatos.pop(0))

    def _planificar(self, env: Entorno) -> None:
        if self.objetivo is None:
            self.ruta = []
            return
        cambio_grafo = self._version != env.version_grafo and self._version != -1
        if not (self._replan or cambio_grafo or (not self.ruta and self.pos != self.objetivo)):
            return
        alg = a_estrella if self.algoritmo == "astar" else dijkstra
        r = alg(env.grafo, self.pos, self.objetivo)
        self.ruta = r.ruta[1:]
        self.costo, self.nodos, self.tiempo_busqueda = r.costo, r.nodos_expandidos, r.tiempo_s
        self._replan, self._version = False, env.version_grafo
        if cambio_grafo:
            self.replanificaciones += 1
            self.bus.registrar(env.tick, f"{self.nombre}: REPLAN por cambio de puerta "
                                         f"({'sin ruta' if not r.ruta else f'costo {r.costo}'})")
        if not r.ruta and self.pos != self.objetivo:         # objetivo inalcanzable
            self.bus.registrar(env.tick, f"{self.nombre}: objetivo {self.objetivo} inalcanzable")
            self.ruta = []
            if self.estado == BUSCAR:
                self._siguiente_candidato(env)
            elif self.estado in (PATRULLA, VOLVER):
                self._avanzar_waypoint()
            elif self.estado == INVESTIGAR:
                self._cambiar(BUSCAR, env)
                self._generar_candidatos(env, self.pos)

    def _ejecutar(self, env: Entorno) -> None:
        if self._espera > 0:
            self._espera -= 1
            return
        if self.ruta and env.mapa.transitable(self.ruta[0]):
            nxt = self.ruta.pop(0)
            self.dir = _DIR.get((nxt[0] - self.pos[0], nxt[1] - self.pos[1]), self.dir)
            self.pos = nxt
            self._espera = self.periodo - 1

    def _evaluar(self, env: Entorno) -> None:
        """¿El plan sigue siendo válido? Si el siguiente paso quedó bloqueado, replanificar."""
        self.visitas[self.pos] = env.tick
        if self.ruta and not env.mapa.transitable(self.ruta[0]):
            self._replan = True

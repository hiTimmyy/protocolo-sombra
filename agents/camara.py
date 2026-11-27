"""Cámara fija con cono de visión: reporta a Nox por el bus."""
from __future__ import annotations

from agents.bus import Bus, Mensaje
from agents.perception import celdas_visibles


class Camara:
    def __init__(self, id: int, pos, direccion: str, bus: Bus, radio: float = 7, angulo: float = 90):
        self.id, self.pos, self.direccion = id, pos, direccion
        self.nombre = f"camara_{id}"
        self.bus, self.radio, self.angulo = bus, radio, angulo
        self.celdas_vistas = []
        self.detecta = False
        self._ultimo_aviso = -999

    def paso(self, env) -> None:
        # Se recalcula cada tick porque las puertas cambian la línea de visión.
        self.celdas_vistas = celdas_visibles(env.mapa, self.pos, self.direccion, self.radio, self.angulo)
        self.detecta = env.nox_pos in self.celdas_vistas
        if self.detecta and env.tick - self._ultimo_aviso >= 8:
            self._ultimo_aviso = env.tick
            self.bus.publicar(Mensaje(env.tick, self.nombre, "AVISTAMIENTO", env.nox_pos))

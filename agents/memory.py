"""Memoria de evidencias (posición, tick) con caducidad (TTL)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

Pos = Tuple[int, int]


@dataclass
class Evidencia:
    pos: Pos
    tick: int          # tick en que se obtuvo la evidencia
    fuente: str        # "vista", "ruido", "camara_0", "guardia_1", "usuario"...


class Memoria:
    def __init__(self, ttl: int):
        self.ttl = ttl                 # ticks que dura una evidencia
        self.items: List[Evidencia] = []

    def agregar(self, pos: Pos, tick: int, fuente: str) -> None:
        if not any(e.pos == pos and e.tick == tick for e in self.items):
            self.items.append(Evidencia(pos, tick, fuente))
            del self.items[:-20]       # límite de tamaño

    def purgar(self, tick_actual: int) -> int:
        """Elimina evidencias caducadas; devuelve cuántas se borraron."""
        antes = len(self.items)
        self.items = [e for e in self.items if tick_actual - e.tick <= self.ttl]
        return antes - len(self.items)

    def vigentes(self, tick_actual: int) -> List[Evidencia]:
        return [e for e in self.items if tick_actual - e.tick <= self.ttl]

    def mas_reciente(self, tick_actual: int) -> Optional[Evidencia]:
        v = self.vigentes(tick_actual)
        return max(v, key=lambda e: e.tick) if v else None

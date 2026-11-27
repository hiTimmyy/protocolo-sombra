"""Bus de mensajes entre guardias y cámaras, con registro (log)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

Pos = Tuple[int, int]


@dataclass
class Mensaje:
    tick: int
    emisor: str                 # "guardia_0", "camara_1", "sistema"...
    tipo: str                   # AVISTAMIENTO, RUIDO, ALARMA, FALSA_ALARMA, PUERTA_BLOQUEADA
    pos: Optional[Pos] = None
    destino: Optional[str] = None   # None = difusión a todos


class Bus:
    def __init__(self):
        self._receptores: Dict[str, Callable[[Mensaje], None]] = {}
        self.log: List[str] = []

    def suscribir(self, nombre: str, receptor: Callable[[Mensaje], None]) -> None:
        self._receptores[nombre] = receptor

    def publicar(self, m: Mensaje) -> None:
        """Entrega el mensaje al destinatario (o a todos menos al emisor) y lo registra."""
        self.log.append(f"[t{m.tick}] {m.emisor} -> {m.destino or 'todos'}: {m.tipo} {m.pos or ''}".strip())
        for nombre, recibir in self._receptores.items():
            if nombre != m.emisor and (m.destino is None or m.destino == nombre):
                recibir(m)

    def registrar(self, tick: int, texto: str) -> None:
        """Anota un evento que no es mensaje (cambio de estado, replaneo...)."""
        self.log.append(f"[t{tick}] {texto}")

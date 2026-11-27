"""Genera las capturas de las 5 escenas para el informe (docs/img/escena_N.png), sin ventana visible.

Uso: python -m game.capturas_escenas
Reutiliza la UI real sobre una simulación "congelada" en el instante de cada escena
(la lógica de las escenas está en bench/demo_escenas.py).
"""
import os
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from bench.demo_escenas import escenas
from game import ui


class _SimCongelada:
    """Devuelve siempre el mismo snapshot (el de la escena)."""

    def __init__(self, sim):
        self._snap = sim.snapshot()

    def snapshot(self):
        return self._snap

    def step(self, accion=None):
        return self._snap


def main() -> None:
    destino = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "img")
    os.makedirs(destino, exist_ok=True)
    for i, (titulo, _, sim) in enumerate(escenas(), start=1):
        ruta = os.path.join(destino, f"escena_{i}.png")

        def capturar(ruta=ruta):
            time.sleep(1.0)
            pygame.image.save(pygame.display.get_surface(), ruta)
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        threading.Thread(target=capturar, daemon=True).start()
        ui.run(_SimCongelada(sim), lambda: None)
        print("guardada", ruta, "-", titulo)


if __name__ == "__main__":
    main()

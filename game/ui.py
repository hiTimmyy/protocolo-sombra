"""Interfaz Pygame (STUB: la implementa el compañero de UI, ver issues #1-#4).

Reglas:
- Solo usar la interfaz de la simulación: sim.step(accion), sim.snapshot(),
  sim.falsa_alarma(pos), sim.bloquear_puerta(id). Tipos en sim/contract.py.
- Mapa por casillas de 16x16 px escalado x2; sprites según assets/README.md
  (si falta un PNG, dibujar un reemplazo por código).
- Teclas: WASD/flechas mover, Shift correr, E hackear, F falsa alarma,
  B bloquear puerta, R reiniciar.
"""


def run(sim) -> None:
    """Bucle principal de la UI. Pendiente de implementar."""
    raise NotImplementedError("La UI se implementa en la rama feat/ui (issues #1-#3).")

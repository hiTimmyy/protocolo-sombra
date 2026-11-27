"""Punto de entrada del juego.

Uso:
    python -m game.main            # abre la ventana con la simulación

Por ahora (issue #2) se usa FakeSimulation para desarrollar la UI.
"""

from sim.fake_sim import FakeSimulation

from game import ui


def main() -> None:
    sim = FakeSimulation()
    ui.run(sim)


if __name__ == "__main__":
    main()

"""Punto de entrada del juego.

Uso:
    python -m game.main                       # simulación real (Simulation)
    python -m game.main --fake                # FakeSimulation (para desarrollar la UI)
    python -m game.main --seed 3 --guardias 3
"""

import argparse

from sim.fake_sim import FakeSimulation
from sim.simulation import Config, Simulation

from game import ui


def main() -> None:
    parser = argparse.ArgumentParser(description="Protocolo Sombra")
    parser.add_argument("--fake", action="store_true",
                        help="usa FakeSimulation en lugar de la simulación real")
    parser.add_argument("--seed", type=int, default=0, help="semilla del mapa")
    parser.add_argument("--guardias", type=int, default=3, help="número de guardias (2 a 4)")
    args = parser.parse_args()

    n_guardias = max(2, min(4, args.guardias))
    if args.fake:
        sim = FakeSimulation()
        fabrica = FakeSimulation
    else:
        sim = Simulation(args.seed, Config(n_guardias=n_guardias))
        fabrica = lambda: Simulation(args.seed, Config(n_guardias=n_guardias))  # reinicio con R

    ui.run(sim, fabrica)


if __name__ == "__main__":
    main()

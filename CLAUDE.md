# Protocolo Sombra — reglas para agentes

Videojuego de sigilo en Python 3.10+ y Pygame. Proyecto final de Algoritmos Computacionales: se evalúan diseño y algoritmos. **No ampliar el alcance** ni sobreingeniería. Sin LLM dentro del juego. Código claro y comentado en español.

## Arquitectura
- `core/graph.py` cuadrícula (`Mapa`) -> grafo (`Grafo`, lista de adyacencia; puerta bloqueada = sin aristas de entrada).
- `core/pathfinding.py` Dijkstra y A* (Manhattan) sobre el mismo grafo -> ruta, costo, nodos_expandidos, tiempo_s.
- `core/recursion.py` DFS recursivo con profundidad limitada (rutas candidatas de búsqueda).
- `agents/` percepción (cono + Bresenham + ruido), memoria con TTL, bus de mensajes, guardia (máquina de estados), cámara.
- `sim/simulation.py` `Simulation(seed, config)` con `step(accion)`, `snapshot()`, `falsa_alarma(pos)`, `bloquear_puerta(id)`. `sim/mapgen.py` genera mapas.
- `sim/contract.py` dataclasses de lo que devuelve `snapshot()` (contrato con la UI). `sim/fake_sim.py` simulación falsa para desarrollar la UI.
- `game/` UI Pygame (solo usa `step/snapshot/falsa_alarma/bloquear_puerta`). `bench/` benchmarks. `tests/` pytest. `docs/` informe y guía.

## Reglas
1. **Prohibido importar pygame** en `core/`, `agents/`, `sim/`. Solo `game/` lo usa.
2. La UI nunca toca internos de la simulación: solo el contrato (`sim/contract.py`). No cambiar el contrato sin avisar.
3. No ampliar alcance: hacer solo lo que pide la issue.
4. Ejecutar `pytest` antes de abrir un PR; debe pasar.
5. En Windows usar `python` (no `python3`).

## Flujo de ramas
- Nadie trabaja directo en `main` ni hace push a `main`. Todo llega por Pull Request (`gh pr create`).
- `dev/core`: lógica (core, agents, sim, bench, tests). `feat/ui`: UI. `docs/informe`: informe y README.
- Crear la rama desde `main` actualizado (`git switch main && git pull && git switch -c <rama>`). Tocar solo los archivos que la issue permite.

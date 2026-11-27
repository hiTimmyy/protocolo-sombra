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

---

# Issues y cómo tomarlas (agente OpenCode)

Las tareas están en GitHub Issues. Cada issue es autocontenida: léela completa y sigue sus pasos.

```
gh issue list                 # ver issues abiertas
gh issue view N               # leer la issue N completa
```

Lista (asignadas a SebastianPalta: #1-#6):
- #1 [ui] Base de la UI con FakeSimulation (rama `feat/ui`)
- #2 [ui] Elementos de juego: guardias, conos, burbujas, cámaras, puertas, hackeo, victoria/derrota, teclas (rama `feat/ui`)
- #3 [ui] Panel de monitoreo y registro de eventos; cambiar a Simulation real con `--fake` (rama `feat/ui`)
- #4 [ui] (opcional) Sprites reales en `assets/sprites` (rama `feat/ui`)
- #5 [docs] Redactar `docs/INFORME.md` y completar `README.md` (rama `docs/informe`)
- #6 [docs] Resultados reales de benchmarks/pruebas en el informe y verificar clon limpio (rama `docs/informe`)
- #7 [core] Lógica (dev/core): NO es de este agente.

Procedimiento: `gh issue view N` -> crear la rama indicada desde `main` actualizado -> hacer los pasos -> verificar los criterios de aceptación -> `git push -u origin <rama>` -> `gh pr create --base main`. Nunca push a `main`.

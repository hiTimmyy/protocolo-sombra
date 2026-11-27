# Guía para redactar `docs/INFORME.md` y `README.md`

Todo lo que se afirme debe poder señalarse en el código. Aquí se indica **dónde está cada cosa**. Los resultados experimentales deben ser los reales de `results/benchmarks.csv` (no inventar números).

## Secciones del informe

1. **Agentes y ciclo percepción → memoria → planificación → decisión → ejecución → evaluación**
   - Agente guardia: `agents/guard.py`, clase `Guardia`, método `paso()` que llama en orden a `_percibir`, `_memorizar`, `_decidir`, `_planificar`, `_ejecutar`, `_evaluar`. (Nota: `_decidir` fija estado y objetivo —qué hacer— y `_planificar` calcula la ruta —cómo—.)
   - Percepción: `agents/perception.py` (`celdas_visibles`, `ve`, `bresenham`, `oye_ruido`, `estimar_posicion_ruido`).
   - Memoria con caducidad (TTL): `agents/memory.py` (`Memoria`, `Evidencia`).
   - Comunicación: `agents/bus.py` (`Bus`, `Mensaje`); cámaras: `agents/camara.py`.
   - Máquina de estados PATRULLA → INVESTIGAR → BUSCAR → ALERTA → VOLVER_A_PATRULLA: `Guardia._decidir`.
   - Simulación y eventos (`falsa_alarma`, `bloquear_puerta`, reorganización de patrullas `asignar_patrullas`): `sim/simulation.py`.
2. **Grafo con V, E y costos**: `core/graph.py` (`Mapa`, `Grafo`, `construir_grafo`). V = casillas no pared; E = aristas dirigidas a las 4 vecinas; costo de arista = costo de la casilla de destino (piso/puerta 1, alfombra 2); puerta bloqueada = sin aristas de entrada. Reportar V y E de los mapas de prueba (`Grafo.V`, `Grafo.E`).
3. **Heurística, admisibilidad y consistencia**: `core/pathfinding.py` (`manhattan`, `a_estrella`). Admisible: cada paso cuesta ≥ 1, así que Manhattan nunca sobreestima. Consistente: `h(a) <= costo(a,b) + h(b)` porque un paso cambia Manhattan en 1 y costo(a,b) ≥ 1. Por eso A* con lista cerrada devuelve costo óptimo (verificado en `tests/test_pathfinding.py` y en `bench/run_benchmarks.py`).
4. **Recursión**: `core/recursion.py`, `rutas_dfs`. Caso base: se alcanzó `profundidad_max` o no hay vecinos sin visitar. Progreso: cada llamada añade una casilla y reduce la profundidad restante. Pila: profundidad máxima = `profundidad_max`. Uso: `Guardia._generar_candidatos` (puntos de búsqueda). Prueba: `tests/test_recursion.py`.
5. **Complejidad teórica**: Dijkstra O((V+E) log V) tiempo, O(V) espacio. A*: mismo orden en el peor caso, expande menos nodos en la práctica. DFS limitado: O(b^d) tiempo (b = ramificación ≤ 3 tras el primer paso, d = profundidad), O(d) pila (más la salida).
6. **Resultados experimentales reales**: ejecutar `python bench/run_benchmarks.py`; usar `results/benchmarks.csv`, `results/resumen.csv`, `results/cobertura.csv` y las gráficas `results/*.png`. Incluir también `results/pruebas.txt` (salida de pytest). Cobertura fija vs dinámica: `bench/run_benchmarks.py`, función `comparar_cobertura`.
7. **Conclusiones y limitaciones**.

## README.md
Completar: instalación (`python -m venv .venv`, activar, `pip install -r requirements.txt`), controles (WASD/flechas, Shift, E, F, B, R), cómo correr juego (`python -m game.main`, `--fake`), tests (`pytest`) y benchmarks.

# Informe — Protocolo Sombra

Videojuego de sigilo en Python y Pygame. El jugador controla a **Nox**, una espía que debe
entrar en una instalación, hackear la terminal y llegar a la extracción mientras guardias
autónomos y cámaras la patrullan. Este informe describe el diseño y los algoritmos del
proyecto; cada afirmación indica el archivo y la función donde está implementada.

## 1. Agentes y ciclo percepción → memoria → planificación → decisión → ejecución → evaluación

El agente principal es la **guardia**, implementada en `agents/guard.py` (clase `Guardia`).
Su ciclo completo de cada tick está en `Guardia.paso()` (`agents/guard.py`), que llama en
orden a:

1. **Percepción** — `Guardia._percibir` (`agents/guard.py`). Calcula el cono de visión con
   `perception.celdas_visibles` (`agents/perception.py`), que combina el test geométrico
   `perception.en_cono` (radio y ángulo) con la línea de visión por **Bresenham**
   (`perception.bresenham` y `perception.hay_linea_de_vision`). También detecta ruido con
   `perception.oye_ruido` (distancia Manhattan contra el radio de audición) y estima de
   dónde viene con `perception.estimar_posicion_ruido` (introduce error aleatorio para no
   ser perfecto), y lee los avisos llegados por el bus (`p.avisos`).
2. **Memoria** — `Guardia._memorizar` (`agents/guard.py`) guarda cada avistamiento, ruido o
   mensaje en `agents/memory.py` (clases `Memoria` y `Evidencia`). La memoria tiene
   **caducidad (TTL)**: `Memoria.purgar` elimina la evidencia vencida y `Memoria.mas_reciente`
   devuelve la evidencia vigente más reciente. Así un guardia "recuerda" dónde vio a Nox
   durante `ttl` ticks (120 por defecto) y después lo olvida.
3. **Decisión** — `Guardia._decidir` (`agents/guard.py`) implementa la **máquina de estados**
   `PATRULLA → INVESTIGAR → BUSCAR → ALERTA → VOLVER_A_PATRULLA`. Fija *qué hacer*: si ve a
   Nox pasa a ALERTA y persigue; si la pierde, investiga la evidencia más reciente; al llegar
   al punto, pasa a BUSCAR alrededor; si la evidencia caduca, vuelve a patrullar. Los cambios
   de estado se anuncian por el bus (`Guardia._cambiar`).
4. **Planificación** — `Guardia._planificar` (`agents/guard.py`) calcula *cómo llegar*: ejecuta
   Dijkstra (`core/pathfinding.py`: `dijkstra`) o A* (`a_estrella`) sobre el grafo del mapa y
   guarda costo, nodos expandidos y tiempo de búsqueda. **Replanifica** si cambió el objetivo,
   si cambió el grafo (puerta bloqueada, detectado con `version_grafo`) o si el siguiente paso
   dejó de ser transitable; cada replanificación por cambio de grafo incrementa
   `Guardia.replanificaciones` y se registra en el log del bus.
5. **Ejecución** — `Guardia._ejecutar` (`agents/guard.py`) avanza una casilla de la ruta cada
   `periodo` ticks (2 en ALERTA/INVESTIGAR, 3 en el resto; ver la propiedad `Guardia.periodo`).
6. **Evaluación** — `Guardia._evaluar` (`agents/guard.py`) comprueba al final del tick si el
   plan sigue válido (el siguiente paso debe ser transitable) y fuerza replanificación si no.

**Comunicación:** `agents/bus.py` (clases `Bus` y `Mensaje`) es un bus pub/sub: los guardias
publican `AVISTAMIENTO` y `RUIDO` (`Guardia._memorizar`) y se suscriben a los mensajes de los
demás (`Bus.suscribir`, `Bus.publicar`); `Bus.registrar` escribe en el log de eventos que la
UI muestra. **Cámaras:** `agents/camara.py` (clase `Camara`, método `paso`) usan el mismo
mecanismo de percepción y publican avisos al bus cuando detectan movimiento.

**La simulación** que orquesta todo está en `sim/simulation.py` (clase `Simulation`,
método `step`). Reparte los puntos de patrulla entre guardias con `asignar_patrullas`
(`sim/simulation.py`) y expone las acciones globales `falsa_alarma(pos)` y
`bloquear_puerta(id)`; tras un bloqueo, `_reorganizar_patrullas` vuelve a repartir los
waypoints alcanzables. El contrato con la UI (los dataclasses de `snapshot()`) está en
`sim/contract.py`, y `sim/fake_sim.py` (`FakeSimulation`) permite desarrollar la interfaz
sin la lógica real.

## 2. Grafo: vértices, aristas y costos

El mapa es una cuadrícula y se convierte en un **grafo de lista de adyacencia** en
`core/graph.py`:

- **Vértices (V):** cada casilla que **no** es pared. La conversión está en
  `construir_grafo` (`core/graph.py`); el número de vértices se consulta con `Grafo.V`.
- **Aristas (E):** dirigidas, hacia las 4 vecinas (arriba, abajo, izquierda, derecha); se
  cuentan con `Grafo.E`. Una arista solo existe si la casilla destino es transitable
  (`Mapa.transitable`).
- **Costos:** el costo de una arista es el costo de **entrar** a la casilla de destino
  (`Mapa.costo`): piso y puerta = 1, alfombra = 2 (`COSTO_TERRENO` en `core/graph.py`).
  Las alfombras son terrain "caro" que los algoritmos evitan si hay ruta equivalente.
- **Puertas bloqueadas:** una puerta bloqueada **no tiene aristas de entrada** (nadie puede
  entrar), pero conserva las de salida para que quien esté encima pueda salir
  (`Mapa.transitable` y la documentación de `core/graph.py`). Al bloquear una puerta la
  simulación reconstruye el grafo e incrementa `version_grafo`, lo que dispara la
  replanificación de los guardias.

Los valores concretos de V y E de los mapas de prueba se reportan en la sección de
resultados (propiedades `Grafo.V` y `Grafo.E`).

## 3. Heurística: admisibilidad y consistencia

A* está en `core/pathfinding.py` (`a_estrella`) y su heurística es la **distancia Manhattan**
(`manhattan`), la misma usada en el resto del proyecto.

- **Admisible** (nunca sobreestima el costo real): todo paso cuesta al menos 1
  (el terreno más barato, piso o puerta, cuesta 1), y Manhattan sube exactamente 1 por paso
  en la mejor de los casos; por tanto h(n) ≤ costo real(n, destino).
- **Consistente** (cumple la desigualdad triangular): para una arista (a, b) con costo
  c(a, b) ≥ 1 se cumple h(a) ≤ c(a, b) + h(b), porque un paso cambia la distancia Manhattan
  a lo sumo en 1 y c(a, b) ≥ 1.

Con una heurística consistente, A* con **lista cerrada** (nodos ya expandidos no se
revisan; ver `a_estrella` en `core/pathfinding.py`) devuelve el camino de costo mínimo,
igual que Dijkstra. La optimalidad se verifica en `tests/test_pathfinding.py` (A* y Dijkstra
coinciden en costo) y en `bench/run_benchmarks.py`.

## 4. Recursión: caso base, progreso y pila

`core/recursion.py` (`rutas_dfs`) implementa un **DFS recursivo con profundidad limitada**
que enumera rutas simples (sin repetir casilla) desde un punto de partida. Se usa en
`Guardia._generar_candidatos` (`agents/guard.py`) para generar los **puntos de búsqueda**
del estado BUSCAR: los extremos de las rutas son casillas plausibles donde puede estar Nox.

- **Caso base:** se alcanza `profundidad_max` (límite de profundidad) o la casilla actual
  no tiene vecinos sin visitar (callejón sin salida). En ambos se registra la ruta actual.
- **Progreso:** cada llamada recursiva añade una casilla al camino y sube la profundidad en
  1, así que la recursión siempre termina en a lo sumo `profundidad_max` niveles.
- **Pila de llamadas:** la profundidad máxima de la pila es `profundidad_max` (más el marco
  inicial); el backtracking se hace con `camino.pop()` y `visitados.remove(v)`.
- **Tope de seguridad:** `max_rutas` limita la explosión combinatoria (en el guardia se usa
  1500; ver `Guardia._generar_candidatos`).

La prueba correspondiente está en `tests/test_recursion.py`.

## 5. Complejidad teórica

- **Dijkstra** (`core/pathfinding.py`: `dijkstra`, con cola de prioridad `heapq` y borrado
  perezoso): tiempo **O((V + E) log V)** y espacio **O(V)** (diccionarios `dist`, `previo` y
  conjunto de cerrados).
- **A*** (`a_estrella`): mismo orden en el peor caso, **O((V + E) log V)** tiempo y **O(V)**
  espacio; en la práctica expande menos nodos que Dijkstra gracias a la heurística Manhattan
  (se compara `nodos_expandidos` en los benchmarks).
- **DFS limitado** (`core/recursion.py`: `rutas_dfs`): tiempo **O(b^d)**, donde b es el
  factor de ramificación (≤ 3 tras el primer paso, porque no se vuelve a la casilla anterior)
  y d la profundidad máxima (`profundidad_busqueda` de la configuración); espacio **O(d)**
  por la pila de llamadas (más la salida, acotada por `max_rutas`).

## 6. Resultados experimentales

TODO resultados

<!-- Issue de resultados: completar con los valores REALES de results/benchmarks.csv,
results/resumen.csv, results/cobertura.csv, results/*.png y results/pruebas.txt
(generados por python bench/run_benchmarks.py y pytest). No inventar números.
Incluir: V y E de los mapas; comparativa Dijkstra vs A* (costo, nodos expandidos, tiempo);
cobertura fija vs dinámica; salida de pytest. -->

## 7. Conclusiones y limitaciones

**Conclusiones:**

- La separación en capas (grafo → pathfinding → agentes → simulación → UI) permite que la
  interfaz (`game/`) funcione contra una simulación real o falsa usando solo el contrato de
  `sim/contract.py`, sin tocar los internos de la lógica.
- La máquina de estados con memoria con TTL y bus de mensajes produce guardias que coordinan
  sus avistamientos sin un controlador central: el conocimiento se propaga por eventos.
- La replanificación reactiva (puertas bloqueadas, evidencias nuevas) hace al sistema
  robusto a cambios del entorno; el costo se paga en búsquedas repetidas, visibles en el
  contador `replanificaciones` del panel de monitoreo.

**Limitaciones:**

- La percepción por cono + Bresenham es por casilla y no modela oclusiones parciales.
- La memoria guarda posiciones puntuales, no trayectorias estimadas de Nox.
- El DFS de búsqueda usa una profundidad fija (`prof_busqueda`), que puede dejar zonas sin
  explorar en mapas con salas grandes.
- Los benchmarks miden tiempo de búsqueda en Python puro; los tiempos absolutos dependen de
  la máquina y no son comparables entre hardware distinto.

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

Resultados reales generados con `python bench/run_benchmarks.py` (equipo: Windows 11,
AMD64, Python 3.14.5; 45 muestras por condición) y `pytest` (salida completa en
`results/pruebas.txt`). Datos crudos: `results/benchmarks.csv`, `results/resumen.csv`,
`results/cobertura.csv`; gráficas: `results/grafica_dijkstra_vs_astar.png` y
`results/grafica_cobertura.png`.

**Tamaño de los grafos** (`Grafo.V`, `Grafo.E` en `core/graph.py`; mapas de
`sim/mapgen.py`, semilla 11):

| Mapa | V (vértices) | E (aristas) |
|---|---|---|
| 20x20 | 134 | 406 |
| 40x40 | 585 | 1782 |
| 80x80 | 2950 | 9390 |
| 160x160 | 16617 | 55344 |

**Dijkstra vs A*** (`results/resumen.csv`; medias de 45 búsquedas por condición):

| Mapa | Dijkstra: tiempo | Dijkstra: nodos | Dijkstra: memoria | A*: tiempo | A*: nodos | A*: memoria |
|---|---|---|---|---|---|---|
| 20x20 | 0.044 ms | 57.0 | 8.8 KB | 0.036 ms | 35.3 | 7.8 KB |
| 40x40 | 0.229 ms | 282.6 | 42.8 KB | 0.144 ms | 139.6 | 23.6 KB |
| 80x80 | 1.143 ms | 1295.0 | 201.3 KB | 0.229 ms | 223.0 | 35.7 KB |
| 160x160 | 9.428 ms | 7865.3 | 1254.7 KB | 1.248 ms | 1037.0 | 192.7 KB |

Lectura de los resultados:

- **El costo de las rutas es idéntico** en todas las condiciones (verificado por el propio
  benchmark: "OK: el costo de A* es igual al de Dijkstra en todas las condiciones"), como
  predice la teoría: con heurística Manhattan admisible y consistente (sección 3), A* es
  óptimo igual que Dijkstra.
- **Nodos expandidos:** A* expande 2-7 veces menos nodos que Dijkstra, y la ventaja crece
  con el tamaño del mapa (en 160x160 expande 1037 frente a 7865, un 87 % menos) porque la
  heurística dirige la búsqueda hacia el destino.
- **Tiempo:** la diferencia se hace evidente en mapas grandes: en 160x160 A* tarda 1.25 ms
  frente a 9.43 ms de Dijkstra (7.6x más rápido). En mapas pequeños el tiempo de ambos es
  del orden de décimas de milisegundo.
- **Memoria pico:** A* también usa menos memoria (193 KB frente a 1255 KB en 160x160),
  porque mantiene menos entradas vivas en la cola y en los diccionarios.
- La ejecución se realizó con la opción por defecto del benchmark (`par=0`, pares
  origen-destino aleatorios por semilla; ver `bench/run_benchmarks.py`).

**Cobertura fija vs dinámica** (`results/cobertura.csv`; 20 semillas, 600 ticks máximo):

| Cobertura | Ticks medios hasta detectar | Detecciones |
|---|---|---|
| Fija | 165.7 | 15 / 20 |
| Dinámica | 130.8 | 16 / 20 |

La cobertura **dinámica** (los guardias reaccionan a ruidos y mensajes del bus,
`cobertura: "dinamica"` en `sim/simulation.py`) detecta antes (130.8 frente a 165.7 ticks)
y en más semillas (16 frente a 15 de 20). En las semillas sin detección (600 = no detectó),
la cobertura fija falla en 1, 4, 10 y 13; la dinámica en 6, 12, 17 y 19: la reactividad
cambia *dónde* falla más que cuántas veces. El detalle por semilla está en
`results/cobertura.csv` y la comparativa en `results/grafica_cobertura.png`
(función `comparar_cobertura` de `bench/run_benchmarks.py`).

**Dijkstra vs A\* con datos reales del juego** (`results/partidas.csv`; función
`comparar_en_partidas` de `bench/run_benchmarks.py`): se simularon 10 partidas completas de
4 guardias con una falsa alarma y el bloqueo de la puerta clave. En cada búsqueda real de un
guardia se ejecutaron Dijkstra y A\* sobre el mismo grafo, origen y destino (comparación
pareada), 249 búsquedas en total:

| Algoritmo | Tiempo medio | Nodos expandidos (media) | Costo medio |
|---|---|---|---|
| Dijkstra | 0.0484 ms | 56.7 | 14.1 |
| A\* | 0.0270 ms | 29.2 | 14.1 |

El costo coincide en las 249 búsquedas (comprobado con una aserción); A\* expande ~48 % menos
nodos y tarda ~44 % menos, en línea con los mapas sintéticos. En este tamaño de mapa (30x20)
ambas búsquedas son del orden de décimas de milisegundo, por lo que no afectan la jugabilidad.

**Pruebas unitarias** (`results/pruebas.txt`, salida completa de `pytest`):

```
============================= 10 passed in 0.28s ==============================
```

10 tests de `tests/test_pathfinding.py` (Dijkstra y A* devuelven costo óptimo, con y sin
camino), `tests/test_recursion.py` (el DFS termina por límite de profundidad y en
callejones) `tests/test_agentes.py` (falsa alarma: el guardia investiga y deja de buscar al caducar la evidencia; puerta bloqueada: replanificación y reorganización de patrullas; hackeo y victoria; simulación completa) y `tests/test_fake_sim.py` (contrato con la UI).

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

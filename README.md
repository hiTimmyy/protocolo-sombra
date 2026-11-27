# Protocolo Sombra

Videojuego de sigilo en Python 3.10+ y Pygame (proyecto final de Algoritmos Computacionales, Fundación Universitaria de Popayán).

Controlas a **Nox**, una espía que debe infiltrarse en la instalación, hackear la terminal y llegar a la zona de extracción mientras guardias autónomos (máquina de estados + Dijkstra/A*) y cámaras la vigilan.

## Qué revisar (guía rápida para la evaluación)

| Entregable | Dónde está |
|---|---|
| **Informe completo** (agentes, grafo, heurística, recursión, complejidad teórica y experimental, pruebas) | [`docs/INFORME.pdf`](docs/INFORME.pdf) (misma versión en [`docs/INFORME.md`](docs/INFORME.md)) |
| **Juego funcional** | `python -m game.main` (ver *Instalación* y *Controles* abajo) |
| **Código fuente** | `core/` (grafo, Dijkstra, A*, recursión), `agents/` (guardias, memoria, bus, percepción), `sim/` (simulación), `game/` (UI) |
| **Resultados experimentales** (semillas, tiempos, costo, nodos, memoria) | `results/benchmarks.csv`, `results/resumen.csv`, `results/partidas.csv`, `results/cobertura.csv` y gráficas `results/*.png` |
| **Resultados de pruebas** | `results/pruebas.txt` (comando: `pytest`) |
| **Demostración de las 5 escenas** | `results/escenas.txt` y capturas en el informe (comando: `python bench/demo_escenas.py`) |

## Instalación

Requisitos: Python 3.10 o superior.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

> **Nota (Python 3.14+):** `pygame` aún no publica wheels para estas versiones. Si la
> instalación falla al compilarlo, instala el fork compatible `pip install pygame-ce`
> (mismas API e imports); el resto de los pasos no cambia.

## Cómo ejecutar el juego

```bash
python -m game.main                      # simulación real
python -m game.main --fake               # simulación de prueba (FakeSimulation)
python -m game.main --seed 3 --guardias 3   # semilla del mapa y guardias (2 a 4)
```

## Controles

| Tecla | Acción |
|---|---|
| `WASD` / flechas | Mover a Nox |
| `Shift` (mantener) | Correr (1 casilla/tick, pero hace ruido) |
| `E` (mantener, junto a la terminal) | Hackear (barra de progreso) |
| `F` | Falsa alarma en la casilla del ratón |
| `B` | Bloquear la primera puerta no bloqueada |
| `Q` | Señuelo de ruido (3 disponibles): distrae al guardia más cercano |
| `R` | Reiniciar la partida |

**Objetivo:** hackea la terminal (`T`) manteniendo `E` y llega a la extracción (`X`) sin que te vean. Si el tiempo se agota o te capturan, pierdes.

## Pruebas y benchmarks

```bash
pytest                            # tests unitarios
python bench/run_benchmarks.py    # benchmarks: genera results/*.csv y results/*.png
```

## Estructura del proyecto

```
core/    # grafo del mapa (Mapa, Grafo), Dijkstra, A* y DFS recursivo
agents/  # percepción (cono + Bresenham), memoria con TTL, bus de mensajes, guardias, cámaras
sim/     # Simulation (step, snapshot, falsa_alarma, bloquear_puerta), generador de mapas, FakeSimulation
game/    # interfaz Pygame (solo usa el contrato de sim/contract.py)
bench/   # benchmarks
tests/   # pruebas pytest
docs/    # informe del proyecto y guía de redacción
```

Más detalles en [`docs/INFORME.md`](docs/INFORME.md).

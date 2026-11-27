# Protocolo Sombra

Videojuego de sigilo en Python 3.10+ y Pygame (proyecto final de Algoritmos Computacionales, Fundación Universitaria de Popayán).

Controlas a **Nox**, una espía que debe infiltrarse en la instalación, hackear la terminal y llegar a la zona de extracción mientras guardias autónomos (máquina de estados + Dijkstra/A*) y cámaras la vigilan.

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

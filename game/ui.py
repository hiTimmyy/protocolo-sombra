"""Interfaz Pygame (issue #2: base de la UI con FakeSimulation).

Reglas:
- Solo se usa la interfaz de la simulación: sim.step(accion), sim.snapshot(),
  sim.falsa_alarma(pos), sim.bloquear_puerta(id). Tipos en sim/contract.py.
- Mapa por casillas de 16x16 px escalado x2; sprites según assets/README.md
  (si falta un PNG, se dibuja un reemplazo por código).
"""
from pathlib import Path

import pygame

from sim.contract import Accion, Snapshot

# Tamaño de casilla: 16 px base escalado x2.
TAM_TILE = 16
ESCALA = 2
TILE = TAM_TILE * ESCALA  # 32 px por casilla
FPS = 30

# Teclas (WASD / flechas) -> dirección que entiende la simulación.
TECLAS_DIRECCION = {
    pygame.K_w: "arriba",
    pygame.K_UP: "arriba",
    pygame.K_s: "abajo",
    pygame.K_DOWN: "abajo",
    pygame.K_a: "izquierda",
    pygame.K_LEFT: "izquierda",
    pygame.K_d: "derecha",
    pygame.K_RIGHT: "derecha",
}

# Colores de respaldo cuando falta un sprite (RPG estilo GBA).
COLOR_PISO = (222, 216, 176)
COLOR_ALFOMBRA = (168, 92, 92)
COLOR_PARED = (88, 88, 104)
COLOR_PUERTA = (150, 106, 62)
COLOR_TERMINAL = (96, 168, 220)
COLOR_EXTRACCION = (110, 200, 120)
COLOR_NOX = (40, 40, 60)

# Nombre de sprite de Nox según dirección (frames de caminar: issue #3).
_SPRITE_NOX = {"arriba": "nox_up_0.png", "abajo": "nox_down_0.png",
               "izquierda": "nox_left_0.png", "derecha": "nox_right_0.png"}


def _carregar_sprite(nombre: str, color: tuple) -> pygame.Surface:
    """Carga assets/sprites/<nombre>; si falta, devuelve un rectángulo de color."""
    superficie = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    ruta = Path(__file__).resolve().parent.parent / "assets" / "sprites" / nombre
    if ruta.is_file():
        img = pygame.image.load(str(ruta)).convert_alpha()
        superficie.blit(pygame.transform.scale(img, (TILE, TILE)), (0, 0))
    else:
        superficie.fill(color)
    return superficie


class _Sprites:
    """Sprites precargados del mapa y de Nox (con reemplazo por código)."""

    def __init__(self) -> None:
        self.tiles = {
            ".": _carregar_sprite("floor.png", COLOR_PISO),
            ",": _carregar_sprite("carpet.png", COLOR_ALFOMBRA),
            "#": _carregar_sprite("wall.png", COLOR_PARED),
            "D": _carregar_sprite("door_closed.png", COLOR_PUERTA),
            "T": _carregar_sprite("terminal.png", COLOR_TERMINAL),
            "X": _carregar_sprite("extraction.png", COLOR_EXTRACCION),
        }
        self.nox = {dir_: _carregar_sprite(nombre, COLOR_NOX)
                    for dir_, nombre in _SPRITE_NOX.items()}


def _dibujar_mapa(ventana: pygame.Surface, snap: Snapshot, sprites: _Sprites) -> None:
    """Dibuja el mapa casilla por casilla desde snapshot.mapa.tiles."""
    for y, fila in enumerate(snap.mapa.tiles):
        for x, caracter in enumerate(fila):
            ventana.blit(sprites.tiles.get(caracter, sprites.tiles["."]), (x * TILE, y * TILE))


def _dibujar_nox(ventana: pygame.Surface, snap: Snapshot, sprites: _Sprites,
                 pos_prev: tuple, fraccion: float) -> None:
    """Dibuja a Nox interpolando visualmente entre la casilla anterior y la nueva."""
    x0, y0 = pos_prev
    x1, y1 = snap.nox.pos
    # Interpolación lineal (la fracción va de 0 a 1 en cada paso de simulación).
    px = round((x0 + (x1 - x0) * fraccion) * TILE)
    py = round((y0 + (y1 - y0) * fraccion) * TILE)
    ventana.blit(sprites.nox.get(snap.nox.direccion, sprites.nox["abajo"]), (px, py))


def run(sim) -> None:
    """Bucle principal de la UI: un paso de simulación cada 1/ticks_por_segundo s."""
    pygame.init()
    snap = sim.snapshot()
    ancho = snap.mapa.ancho * TILE
    alto = snap.mapa.alto * TILE
    ventana = pygame.display.set_mode((ancho, alto))
    pygame.display.set_caption("Protocolo Sombra")
    reloj = pygame.time.Clock()
    sprites = _Sprites()

    paso_s = 1.0 / max(1, snap.ticks_por_segundo)
    acumulado = 0.0        # tiempo desde el último paso de simulación
    pos_prev = snap.nox.pos  # casilla de Nox antes del último paso (interpolación)
    activo = True

    while activo:
        # Entrada: WASD / flechas -> Accion(mover=...) para sim.step.
        mover = None
        for tecla, direccion in TECLAS_DIRECCION.items():
            if pygame.key.get_pressed()[tecla]:
                mover = direccion
                break
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                activo = False
        accion = Accion(mover=mover)

        # Avance del tiempo: se ejecuta un paso de simulación cuando toca.
        dt = reloj.tick(FPS) / 1000.0
        acumulado += dt
        while acumulado >= paso_s and activo:
            pos_prev = snap.nox.pos
            snap = sim.step(accion)
            acumulado -= paso_s
            if snap.resultado != "jugando":  # victoria/derrota: se detiene el bucle
                activo = False

        # Dibujo.
        fraccion = max(0.0, min(1.0, acumulado / paso_s))
        _dibujar_mapa(ventana, snap, sprites)
        _dibujar_nox(ventana, snap, sprites, pos_prev, fraccion)
        pygame.display.flip()

    pygame.quit()

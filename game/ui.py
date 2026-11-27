"""Interfaz Pygame (issues #2 y #3: base + elementos de juego con FakeSimulation).

Reglas:
- Solo se usa la interfaz de la simulación: sim.step(accion), sim.snapshot(),
  sim.falsa_alarma(pos), sim.bloquear_puerta(id). Tipos en sim/contract.py.
- Mapa por casillas de 16x16 px escalado x2; sprites según assets/README.md
  (si falta un PNG, se dibuja un reemplazo por código).
- Teclas: WASD/flechas mover, Shift correr, E hackear, F falsa alarma,
  B bloquear puerta, R reiniciar.
"""
from pathlib import Path

import pygame

from sim.contract import Accion, Snapshot, PuertaSnap
from sim.fake_sim import FakeSimulation

# Tamaño de casilla: 16 px base escalado x2.
TAM_TILE = 16
ESCALA = 2
TILE = TAM_TILE * ESCALA  # 32 px por casilla
FPS = 30
ANCHO_PANEL = 280         # panel de monitoreo a la derecha del mapa

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
COLOR_PUERTA_ABIERTA = (120, 96, 66)
COLOR_PUERTA_CERRADA = (150, 106, 62)
COLOR_PUERTA_BLOQUEADA = (60, 60, 70)
COLOR_TERMINAL = (96, 168, 220)
COLOR_EXTRACCION = (110, 200, 120)
COLOR_NOX = (40, 40, 60)
COLOR_GUARDIA = (150, 50, 50)
COLOR_CAMARA = (70, 80, 95)
COLOR_CONO = (250, 235, 120, 70)      # translúcido (RGBA)
COLOR_VISION_CAMARA = (120, 200, 255, 60)  # translúcido (RGBA)
COLOR_BURBUJA_VE = (220, 60, 50)      # burbuja "!"
COLOR_BURBUJA_BUSCA = (230, 180, 60)  # burbuja "?"
COLOR_BARRA_FONDO = (30, 30, 40)
COLOR_BARRA_HACKEO = (90, 200, 120)
COLOR_PANEL_FONDO = (28, 28, 36)
COLOR_PANEL_BORDE = (170, 170, 190)
COLOR_PANEL_TEXTO = (225, 225, 225)
COLOR_PANEL_TITULO = (250, 230, 170)

# Nivel de alerta global -> color del indicador.
COLOR_ALERTA = {"verde": (110, 200, 120), "amarilla": (230, 200, 80), "roja": (220, 80, 80)}


def _cargar_sprite(nombre: str, color: tuple) -> pygame.Surface:
    """Carga assets/sprites/<nombre>; si falta, devuelve un rectángulo de color."""
    superficie = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    ruta = Path(__file__).resolve().parent.parent / "assets" / "sprites" / nombre
    if ruta.is_file():
        img = pygame.image.load(str(ruta)).convert_alpha()
        superficie.blit(pygame.transform.scale(img, (TILE, TILE)), (0, 0))
    else:
        superficie.fill(color)
    return superficie


def _secuencia(prefijo: str, color: tuple) -> list:
    """Carga los 3 frames de una secuencia (0 = quieta, 1-2 = caminando)."""
    return [_cargar_sprite(f"{prefijo}_{i}.png", color) for i in range(3)]


# Los PNG usan nombres en inglés (assets/README.md); la simulación usa direcciones en español.
_DIR_ARCHIVO = {"arriba": "up", "abajo": "down", "izquierda": "left", "derecha": "right"}

# Ayuda de controles que se muestra al pie del panel.
AYUDA_CONTROLES = ["WASD/flechas: mover", "Shift: correr (hace ruido)", "E: hackear (junto a la terminal)",
                   "R: reiniciar"]  # + Q (señuelo) y, con --debug, F/B se añaden en el panel
AYUDA_DEBUG = ["[debug] F: falsa alarma (casilla del ratón)", "[debug] B: bloquear la siguiente puerta"]


class _Sprites:
    """Sprites precargados del mapa, personajes y burbujas (con respaldo por código)."""

    def __init__(self) -> None:
        self.tiles = {
            ".": _cargar_sprite("floor.png", COLOR_PISO),
            ",": _cargar_sprite("carpet.png", COLOR_ALFOMBRA),
            "#": _cargar_sprite("wall.png", COLOR_PARED),
            "T": _cargar_sprite("terminal.png", COLOR_TERMINAL),
            "X": _cargar_sprite("extraction.png", COLOR_EXTRACCION),
        }
        self.puertas = {
            "abierta": _cargar_sprite("door_open.png", COLOR_PUERTA_ABIERTA),
            "cerrada": _cargar_sprite("door_closed.png", COLOR_PUERTA_CERRADA),
            "bloqueada": _cargar_sprite("door_blocked.png", COLOR_PUERTA_BLOQUEADA),
        }
        self.nox = {d: _secuencia(f"nox_{_DIR_ARCHIVO[d]}", COLOR_NOX)
                    for d in ("arriba", "abajo", "izquierda", "derecha")}
        self.guard = {d: _secuencia(f"guard_{_DIR_ARCHIVO[d]}", COLOR_GUARDIA)
                      for d in ("arriba", "abajo", "izquierda", "derecha")}
        self.camara = _cargar_sprite("camera.png", COLOR_CAMARA)
        self.burbujas = {
            "!": _cargar_sprite("bubble_alert.png", COLOR_BURBUJA_VE),
            "?": _cargar_sprite("bubble_question.png", COLOR_BURBUJA_BUSCA),
        }


def _estado_puertas(snap: Snapshot) -> dict:
    """Mapa posición -> estado de puerta ("abierta"/"cerrada"/"bloqueada")."""
    return {p.pos: p.estado for p in snap.mapa.puertas}


def _frame_animacion(moviendo: bool, fraccion: float) -> int:
    """Índice de frame: 0 si quieta; alterna 1-2 mientras camina."""
    if not moviendo:
        return 0
    return 1 if fraccion < 0.5 else 2


def _interpolar(p0: tuple, p1: tuple, fraccion: float) -> tuple:
    """Interpolación lineal entre dos casillas; devuelve píxeles."""
    x0, y0 = p0
    x1, y1 = p1
    return (round((x0 + (x1 - x0) * fraccion) * TILE),
            round((y0 + (y1 - y0) * fraccion) * TILE))


def _dibujar_mapa(ventana: pygame.Surface, snap: Snapshot, sprites: _Sprites) -> None:
    """Dibuja piso, paredes, alfombras, terminal, extracción y puertas (3 estados)."""
    estados = _estado_puertas(snap)
    for y, fila in enumerate(snap.mapa.tiles):
        for x, caracter in enumerate(fila):
            pos_px = (x * TILE, y * TILE)
            if caracter == "D":
                ventana.blit(sprites.puertas[estados.get((x, y), "cerrada")], pos_px)
            else:
                ventana.blit(sprites.tiles.get(caracter, sprites.tiles["."]), pos_px)


def _dibujar_visiones(ventana: pygame.Surface, snap: Snapshot) -> None:
    """Dibuja conos de visión de guardias y celdas de cámaras (translúcidos)."""
    capa = pygame.Surface(ventana.get_size(), pygame.SRCALPHA)
    for guardia in snap.guardias:
        for (x, y) in guardia.cono:
            capa.fill(COLOR_CONO, (x * TILE, y * TILE, TILE, TILE))
    for camara in snap.camaras:
        for (x, y) in camara.celdas_vistas:
            capa.fill(COLOR_VISION_CAMARA, (x * TILE, y * TILE, TILE, TILE))
    ventana.blit(capa, (0, 0))


def _dibujar_camaras(ventana: pygame.Surface, snap: Snapshot, sprites: _Sprites) -> None:
    for camara in snap.camaras:
        x, y = camara.pos
        ventana.blit(sprites.camara, (x * TILE, y * TILE))


def _dibujar_personaje(ventana: pygame.Surface, secuencia: list, pos_px: tuple,
                       moviendo: bool, fraccion: float) -> None:
    ventana.blit(secuencia[_frame_animacion(moviendo, fraccion)], pos_px)


def _dibujar_burbuja(ventana: pygame.Surface, sprites: _Sprites, pos_px: tuple,
                     burbuja: str) -> None:
    """Burbuja "!" o "?" sobre el guardia; respaldo: círculo con la letra."""
    if burbuja not in sprites.burbujas:
        return
    px, py = pos_px
    ventana.blit(sprites.burbujas[burbuja], (px, py - TILE // 2))


def _dibujar_barra_hackeo(ventana: pygame.Surface, pos_px: tuple, progreso: float) -> None:
    """Barra de progreso del hackeo sobre Nox (0.0 - 1.0)."""
    if progreso <= 0.0:
        return
    px, py = pos_px
    ancho, alto = TILE, 6
    fondo = pygame.Rect(px, py - 10, ancho, alto)
    pygame.draw.rect(ventana, COLOR_BARRA_FONDO, fondo)
    pygame.draw.rect(ventana, COLOR_BARRA_HACKEO,
                     (px, py - 10, int(ancho * progreso), alto))


def _dibujar_escena(ventana: pygame.Surface, snap: Snapshot, sprites: _Sprites,
                    fuente: pygame.font.Font, nox_prev: tuple, guardias_prev: dict,
                    fraccion: float) -> None:
    """Dibuja un fotograma completo de la partida."""
    _dibujar_mapa(ventana, snap, sprites)
    _dibujar_visiones(ventana, snap)
    _dibujar_camaras(ventana, snap, sprites)

    # Guardias: posición interpolada, animación y burbuja de estado.
    for guardia in snap.guardias:
        prev = guardias_prev.get(guardia.id, guardia.pos)
        moviendo = prev != guardia.pos
        pos_px = _interpolar(prev, guardia.pos, fraccion)
        _dibujar_personaje(ventana, sprites.guard.get(guardia.direccion, sprites.guard["abajo"]),
                           pos_px, moviendo, fraccion)
        _dibujar_burbuja(ventana, sprites, pos_px, guardia.burbuja)

    # Nox: posición interpolada y barra de hackeo.
    moviendo_nox = nox_prev != snap.nox.pos
    nox_px = _interpolar(nox_prev, snap.nox.pos, fraccion)
    _dibujar_personaje(ventana, sprites.nox.get(snap.nox.direccion, sprites.nox["abajo"]),
                       nox_px, moviendo_nox, fraccion)
    _dibujar_barra_hackeo(ventana, nox_px, snap.nox.hackeo_progreso)


def _dibujar_fin(ventana: pygame.Surface, snap: Snapshot, fuente: pygame.font.Font) -> None:
    """Pantalla de victoria / derrota con indicación de reinicio (centrada en el mapa)."""
    velo = pygame.Surface(ventana.get_size(), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 170))
    ventana.blit(velo, (0, 0))
    if snap.resultado == "gano":
        texto, color = "¡VICTORIA! Archivo obtenido", (120, 220, 140)
    else:
        texto, color = "DERROTA", (220, 90, 90)
    cx = (ventana.get_width() - ANCHO_PANEL) // 2
    cy = ventana.get_height() // 2
    render = fuente.render(texto, True, color)
    ventana.blit(render, render.get_rect(center=(cx, cy - 15)))
    ayuda = fuente.render("Pulsa R para reiniciar", True, (230, 230, 230))
    ventana.blit(ayuda, ayuda.get_rect(center=(cx, cy + 25)))


def _texto(ventana: pygame.Surface, fuente: pygame.font.Font, contenido: str,
           pos: tuple, color: tuple = COLOR_PANEL_TEXTO) -> None:
    ventana.blit(fuente.render(contenido, True, color), pos)


def _caja(ventana: pygame.Surface, rect: pygame.Rect) -> None:
    """Caja estilo menú RPG: fondo oscuro y borde claro."""
    pygame.draw.rect(ventana, COLOR_PANEL_FONDO, rect, border_radius=4)
    pygame.draw.rect(ventana, COLOR_PANEL_BORDE, rect, 2, border_radius=4)


def _dibujar_panel(ventana: pygame.Surface, snap: Snapshot, debug: bool,
                   fuente_tit: pygame.font.Font, fuente_txt: pygame.font.Font) -> None:
    """Panel de monitoreo: alerta global, tiempo restante, guardias y registro."""
    x0 = ventana.get_width() - ANCHO_PANEL
    pygame.draw.rect(ventana, COLOR_PANEL_FONDO, (x0, 0, ANCHO_PANEL, ventana.get_height()))

    # Indicador de alerta global y tiempo restante.
    color_alerta = COLOR_ALERTA.get(snap.alerta, COLOR_PANEL_TEXTO)
    pygame.draw.circle(ventana, color_alerta, (x0 + 16, 18), 8)
    _texto(ventana, fuente_tit, f"ALERTA {snap.alerta.upper()}", (x0 + 32, 9), color_alerta)
    _texto(ventana, fuente_tit, f"{snap.tiempo_restante_s:5.1f} s",
           (x0 + ANCHO_PANEL - 90, 9))

    # Una caja por guardia con sus datos de monitoreo (solo desde el snapshot).
    y = 36
    alto_caja = 92
    for guardia in snap.guardias:
        if y + alto_caja > ventana.get_height():
            break
        rect = pygame.Rect(x0 + 6, y, ANCHO_PANEL - 12, alto_caja)
        _caja(ventana, rect)
        _texto(ventana, fuente_tit, f"Guardia {guardia.id}: {guardia.estado}",
               (rect.x + 8, y + 6), COLOR_PANEL_TITULO)
        objetivo = guardia.objetivo if guardia.objetivo is not None else "-"
        lineas = [
            f"objetivo: {objetivo} | ruta: {len(guardia.ruta)} casillas",
            f"percibe: {guardia.percepcion}",
            f"{guardia.algoritmo} ({guardia.heuristica}) | costo {guardia.costo:.1f}",
            f"nodos {guardia.nodos_expandidos} | "
            f"{guardia.tiempo_busqueda_s * 1000:.1f} ms | replan {guardia.replanificaciones}",
        ]
        for i, linea in enumerate(lineas):
            _texto(ventana, fuente_txt, linea, (rect.x + 8, y + 28 + i * 14))
        y += alto_caja + 6

    # Caja de registro: últimas líneas de snapshot.log (desplazamiento al final).
    if y < ventana.get_height() - 10:
        rect = pygame.Rect(x0 + 6, y, ANCHO_PANEL - 12, ventana.get_height() - y - 6)
        _caja(ventana, rect)
        _texto(ventana, fuente_tit, "Registro", (rect.x + 8, y + 6), COLOR_PANEL_TITULO)
        alto_linea = 14
        primeras = rect.y + 28
        ayuda_y = rect.bottom - 6 - (len(AYUDA_CONTROLES) + 1 + (len(AYUDA_DEBUG) if debug else 0)) * alto_linea
        max_lineas = max(0, (ayuda_y - 4 - primeras) // alto_linea)
        ayuda = AYUDA_CONTROLES + [f"Q: señuelo de ruido ({snap.nox.senuelos} restantes)"] + (AYUDA_DEBUG if debug else [])
        for i, linea in enumerate(ayuda):
            _texto(ventana, fuente_txt, linea, (rect.x + 8, ayuda_y + i * alto_linea), COLOR_PANEL_TITULO)
        for i, linea in enumerate(snap.log[-max_lineas:]):
            _texto(ventana, fuente_txt, linea, (rect.x + 8, primeras + i * alto_linea))


def run(sim, fabrica=None, debug: bool = False) -> None:
    """Bucle principal de la UI: un paso de simulación cada 1/ticks_por_segundo s.

    `fabrica` se usa al reiniciar con R (crea una simulación nueva); si es None,
    se reinicia con FakeSimulation.
    """
    if fabrica is None:
        fabrica = FakeSimulation
    pygame.init()
    snap = sim.snapshot()
    ventana = pygame.display.set_mode((snap.mapa.ancho * TILE + ANCHO_PANEL,
                                       snap.mapa.alto * TILE))
    pygame.display.set_caption("Protocolo Sombra")
    reloj = pygame.time.Clock()
    fuente = pygame.font.SysFont(None, 28)      # textos grandes (pantalla de fin)
    fuente_tit = pygame.font.SysFont(None, 20)  # títulos del panel
    fuente_txt = pygame.font.SysFont(None, 16)  # texto del panel
    sprites = _Sprites()

    activo = True
    while activo:
        # Estado local de cada intento (se reinicia con R).
        paso_s = 1.0 / max(1, snap.ticks_por_segundo)
        acumulado = 0.0
        nox_prev = snap.nox.pos
        guardias_prev = {g.id: g.pos for g in snap.guardias}
        reiniciar = False
        senuelo_pendiente = False

        while activo and not reiniciar:
            # Entrada continua: mover (WASD/flechas), correr (Shift), hackear (E).
            mover = None
            teclas = pygame.key.get_pressed()
            for tecla, direccion in TECLAS_DIRECCION.items():
                if teclas[tecla]:
                    mover = direccion
                    break
            accion = Accion(mover=mover,
                            correr=bool(teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]),
                            interactuar=bool(teclas[pygame.K_e]))

            # Entrada puntual: falsa alarma (F), bloquear puerta (B), reiniciar (R).
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    activo = False
                elif evento.type == pygame.KEYDOWN:
                    if debug and evento.key == pygame.K_f:        # solo con --debug (eventos de prueba)
                        mx, my = pygame.mouse.get_pos()
                        casilla = (mx // TILE, my // TILE)
                        dentro = 0 <= casilla[0] < snap.mapa.ancho and 0 <= casilla[1] < snap.mapa.alto
                        sim.falsa_alarma(casilla if dentro else snap.nox.pos)
                    elif debug and evento.key == pygame.K_b:      # solo con --debug
                        for puerta in snap.mapa.puertas:
                            if puerta.estado != "bloqueada":
                                sim.bloquear_puerta(puerta.id)
                                break
                    elif evento.key == pygame.K_q:
                        senuelo_pendiente = True
                    elif evento.key == pygame.K_r:
                        reiniciar = True  # sale para crear una simulación nueva

            if reiniciar:
                break
            accion.senuelo = senuelo_pendiente

            if snap.resultado == "jugando":
                # Avance del tiempo: un paso de simulación cuando toca.
                acumulado += reloj.tick(FPS) / 1000.0
                while acumulado >= paso_s:
                    nox_prev = snap.nox.pos
                    guardias_prev = {g.id: g.pos for g in snap.guardias}
                    snap = sim.step(accion)
                    accion.senuelo = senuelo_pendiente = False
                    acumulado -= paso_s
                    if snap.resultado != "jugando":
                        break
                fraccion = max(0.0, min(1.0, acumulado / paso_s))
            else:
                reloj.tick(FPS)  # pantalla de fin: se espera R o cierre
                fraccion = 1.0

            # Dibujo de la escena (y pantalla de fin si ganó o perdió).
            _dibujar_escena(ventana, snap, sprites, fuente,
                            nox_prev, guardias_prev, fraccion)
            _dibujar_panel(ventana, snap, debug, fuente_tit, fuente_txt)
            if snap.resultado != "jugando":
                _dibujar_fin(ventana, snap, fuente)
            pygame.display.flip()

        if activo:
            sim = fabrica()  # R: reiniciar con una simulación nueva
            snap = sim.snapshot()

    pygame.quit()

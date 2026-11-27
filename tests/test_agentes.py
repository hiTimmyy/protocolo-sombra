"""Pruebas de comportamiento: falsa alarma y puerta bloqueada (replanificación y patrullas)."""
from sim.contract import Accion
from agents.guard import BUSCAR, INVESTIGAR, PATRULLA, VOLVER
from core.graph import Mapa
from sim.simulation import Config, Simulation

# Sala grande (guardia) y bolsillo aislado donde empieza Nox (sin contacto visual ni camino).
SALA = [
    "###########",
    "#.........#",
    "#.........#",
    "#.........#",
    "#.........#",
    "###########",
    "#N#T#X#####",
    "###########",
]


def _sim_sala(ttl=40):
    m = Mapa.desde_ascii(SALA)
    m.waypoints = [(2, 2)]
    cfg = Config(ttl_evidencia=ttl, guardias_inicio=[(2, 2)], camaras_inicio=[], n_guardias=1)
    return Simulation(1, cfg, mapa=m)


def test_falsa_alarma_investiga_y_deja_de_buscar_al_caducar():
    sim = _sim_sala(ttl=40)
    g = sim.guardias[0]
    sim.falsa_alarma((8, 3))
    sim.step()
    assert g.estado == INVESTIGAR and g.objetivo == (8, 3)
    estados = set()
    for _ in range(80):
        sim.step()
        estados.add(g.estado)
        if sim.tick == 30:
            assert g.estado in (INVESTIGAR, BUSCAR)      # la evidencia sigue vigente
    assert BUSCAR in estados                              # llegó y buscó alrededor
    assert g.memoria.vigentes(sim.tick) == []             # la evidencia venció
    assert g.estado in (VOLVER, PATRULLA)                 # dejó de buscar
    for _ in range(60):
        sim.step()
        assert g.estado in (VOLVER, PATRULLA)             # no vuelve a buscar solo


# Dos salas unidas por una puerta (arriba) y un pasillo (abajo); otra sala solo con puerta.
DOBLE = [
    "###############",
    "#.....#.......#",
    "#.....D.......#",   # puerta (6,2): ruta corta
    "#.....#.......#",
    "#.....#.......#",
    "#.............#",   # ruta alterna por abajo
    "#######D#######",   # puerta (7,6) a sala aislada
    "#######.#######",
    "###############",
]


def test_puerta_bloqueada_replanifica_y_reorganiza_patrullas():
    m = Mapa.desde_ascii(DOBLE)
    m.entrada = (1, 1)
    m.waypoints = [(2, 2), (10, 2), (7, 7)]
    cfg = Config(guardias_inicio=[(2, 2), (10, 4)], camaras_inicio=[], n_guardias=2)
    sim = Simulation(1, cfg, mapa=m)
    sim.nox.pos = (1, 4)                                  # lejos de la vista de los guardias
    g0 = sim.guardias[0]
    g0.waypoints, g0.wp_idx = [(10, 2)], 0
    g0._fijar_objetivo((10, 2))
    for _ in range(4):
        sim.step()
    assert (6, 2) in g0.ruta                              # ruta corta por la puerta
    antes = g0.replanificaciones
    sim.bloquear_puerta(0)
    sim.step()
    assert g0.replanificaciones == antes + 1
    assert (6, 2) not in g0.ruta and g0.ruta              # rodea por el pasillo de abajo
    sim.bloquear_puerta(1)                                # aísla la sala de (7,7)
    alc = [sim.grafo.alcanzables(g.pos) for g in sim.guardias]
    for g, a in zip(sim.guardias, alc):
        assert all(w in a for w in g.waypoints)           # patrullas solo con puntos alcanzables
    assert (7, 7) not in sim.guardias[0].waypoints + sim.guardias[1].waypoints


def test_simulacion_completa_corre():
    sim = Simulation(3)
    s = sim.step()
    for _ in range(200):
        s = sim.step()
    assert s.tick == 201 and len(s.guardias) == 3 and len(s.camaras) == 2
    assert s.mapa.tiles[s.mapa.terminal[1]][s.mapa.terminal[0]] == "T"


def test_hackeo_alerta_global_y_victoria():
    m = Mapa.desde_ascii(["#########", "#N.T...X#", "#########"])
    sim = Simulation(1, Config(guardias_inicio=[], camaras_inicio=[]), mapa=m)
    for _ in range(2):
        sim.step(Accion(mover="derecha"))
        sim.step(Accion(mover="derecha"))
    assert sim.nox.pos == (3, 1)
    for _ in range(31):                                   # ~3 s de hackeo
        s = sim.step(Accion(interactuar=True))
    assert s.nox.tiene_archivo and s.alerta == "roja"
    for _ in range(40):
        s = sim.step(Accion(mover="derecha", correr=True))
    assert s.resultado == "gano"


def test_patrulla_usa_dfs_y_recorre_mas_que_los_waypoints():
    sim = _sim_sala()
    g = sim.guardias[0]
    for _ in range(300):
        sim.step()
    assert g.tramos_dfs > 0                       # eligió tramos con el DFS recursivo limitado
    assert len(g.visitas) > 10                    # cubrió muchas casillas, no solo el waypoint


SALIDAS = [
    "###############",
    "#N....#.......#",
    "#.T...D......X#",   # puerta clave (6,2) en la ruta corta
    "#.....#.......#",
    "#.............#",   # ruta alterna por abajo
    "###############",
]


def test_hackeo_bloquea_puerta_y_guardias_cubren_salidas():
    m = Mapa.desde_ascii(SALIDAS)
    m.puerta_clave = 0
    m.waypoints = [(12, 2)]
    cfg = Config(guardias_inicio=[(12, 1), (12, 3)], camaras_inicio=[], alarma_ticks=5)
    sim = Simulation(1, cfg, mapa=m)
    sim.nox.pos = (2, 2)
    for _ in range(31):
        sim.step(Accion(interactuar=True))
    assert sim.mapa.puertas[0].estado == "bloqueada"
    assert any((13, 2) in g.waypoints for g in sim.guardias)       # cubren la extracción
    assert any("cubren rutas de salida" in l for l in sim.bus.log)
    for _ in range(6):
        sim.step()
    assert all((13, 2) not in g.waypoints for g in sim.guardias)   # fin de la alerta: patrullas normales


def test_senuelo_distrae_al_guardia_mas_cercano():
    sim = _sim_sala()
    sim.step(Accion(senuelo=True))
    assert sim.nox.senuelos == 2
    assert sim.guardias[0].estado in (INVESTIGAR, BUSCAR)
    lejos = Simulation(1, Config(radio_senuelo=1, guardias_inicio=[(2, 2)], camaras_inicio=[], n_guardias=1),
                       mapa=Mapa.desde_ascii(SALA))
    lejos.step(Accion(senuelo=True))
    assert lejos.guardias[0].estado == PATRULLA and any("ningún guardia" in l for l in lejos.bus.log)

"""Demostración reproducible de las 5 escenas del storyboard (sin ventana).

Uso: python bench/demo_escenas.py   -> imprime y guarda results/escenas.txt
`escenas(seed)` también la usa bench/capturas_escenas.py para generar las capturas del informe.
(La posición de Nox se coloca a mano en algunas escenas solo para acortar la demostración.)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.contract import Accion
from sim.simulation import Config, Simulation

SEMILLA = 3


def _estados(sim):
    return ", ".join(f"{g.nombre}={g.estado}" for g in sim.guardias)


def _alejar_guardias(sim, punto):
    """Solo para la demostración: coloca a los guardias lejos de `punto` en estado de patrulla."""
    lejos = sorted(sim.mapa.waypoints, key=lambda w: -(abs(w[0] - punto[0]) + abs(w[1] - punto[1])))
    for i, g in enumerate(sim.guardias):
        g.pos, g.ruta, g.estado = lejos[i % len(lejos)], [], "PATRULLA"
        g.memoria.items.clear()
        g.asignar_waypoints(g.waypoints)


def escenas(seed: int = SEMILLA):
    """Genera (titulo, descripcion, simulacion) para cada escena, avanzando la misma partida."""
    sim = Simulation(seed, Config(n_guardias=3, ttl_evidencia=60))
    m = sim.mapa
    for _ in range(5):
        sim.step()
    yield ("Escena 1 · Perímetro",
           f"Nox entra por {m.entrada}. Los guardias patrullan sectores asignados con waypoints y "
           f"tramos DFS; las cámaras vigilan sus conos. Estados: {_estados(sim)}.", sim)

    # Escena 2: anomalía (falsa alarma / ruido) -> el guardia más cercano investiga y luego busca.
    sim.nox.pos = m.entrada
    sim.falsa_alarma(m.waypoints[len(m.waypoints) // 2])
    for _ in range(40):
        sim.step()
    yield ("Escena 2 · Anomalía",
           f"Falsa alarma en {m.waypoints[len(m.waypoints) // 2]}: el guardia más cercano investiga la "
           f"ubicación estimada y luego busca alrededor (DFS limitado). Estados: {_estados(sim)}.", sim)

    # Escena 3: acceso al archivo -> alerta global, mensajes, reorganización de patrullas.
    _alejar_guardias(sim, m.terminal)
    sim.nox.pos = (m.terminal[0] - 1, m.terminal[1]) if not sim.mapa.es_pared((m.terminal[0] - 1, m.terminal[1])) \
        else m.terminal
    vision = [(o, o.radio_vision if hasattr(o, "radio_vision") else o.radio) for o in sim.guardias + sim.camaras]
    for g in sim.guardias:                       # demostración: guardias quietos mientras Nox hackea
        g._espera = 10_000
    for o, _ in vision:                          # ... y nadie la ve
        setattr(o, "radio_vision" if hasattr(o, "radio_vision") else "radio", 0)
    for _ in range(int(sim.cfg.hackeo_s * sim.cfg.ticks_por_segundo) + 1):
        sim.step(Accion(interactuar=True))
        if sim.resultado != "jugando":
            break
    yield ("Escena 3 · Alerta",
           "Nox hackea la terminal: alerta global roja, mensaje ALARMA por el bus, la puerta clave se "
           f"bloquea y las patrullas se reorganizan. Alerta: {sim._alerta()}.", sim)

    for g in sim.guardias:
        g._espera = 0
    for o, r in vision:
        setattr(o, "radio_vision" if hasattr(o, "radio_vision") else "radio", r)
    sim.nox.pos = m.entrada                      # Nox huye de la terminal

    # Escena 4: doble ruta -> rutas alternativas y cobertura de salidas.
    for _ in range(10):
        sim.step()
    yield ("Escena 4 · Doble ruta",
           "La puerta clave quedó bloqueada: el grafo se reconstruye, los guardias replanifican "
           "(contador replan) y reparten la vigilancia de las rutas de salida hacia la extracción. "
           "Replaneos: " + ", ".join(f"{g.nombre}={g.replanificaciones}" for g in sim.guardias) + ".", sim)

    # Escena 5: extracción -> la evidencia caduca, los guardias alternan búsqueda/retorno y Nox sale.
    sim.nox.pos = m.entrada                      # Nox se aleja mientras la evidencia caduca
    for _ in range(sim.cfg.ttl_evidencia + 120):
        if sim.resultado != "jugando":
            break
        sim.step()
    estados = _estados(sim)
    sim.nox.pos = m.extraccion
    sim.step()
    yield ("Escena 5 · Extracción",
           "Tras la alerta, la evidencia del terminal caduca (TTL) y los guardias alternan BÚSQUEDA y "
           f"RETORNO a patrulla (estados antes de la salida: {estados}). Nox alcanza la extracción con el "
           f"archivo: resultado = {sim.resultado}.", sim)


def main():
    salida, nuevas, pendientes = [], 0, []
    es_ruta = lambda l: any(k in l for k in ("REPLAN", "cubren", "PUERTA_BLOQUEADA", "reorganizadas"))
    for titulo, desc, sim in escenas():
        lineas = sim.bus.log[nuevas:]
        nuevas = len(sim.bus.log)
        if titulo.startswith("Escena 3"):          # los eventos de ruta pertenecen a la escena 4
            pendientes = [l for l in lineas if es_ruta(l)]
            lineas = [l for l in lineas if not es_ruta(l)]
        elif titulo.startswith("Escena 4"):
            lineas = pendientes + lineas
        salida += [f"=== {titulo} (tick {sim.tick}) ===", desc, "Registro del bus (nuevas líneas):"]
        salida += [f"  {l}" for l in lineas] or ["  (sin eventos)"]
        salida.append("")
    texto = "\n".join(salida)
    print(texto)
    destino = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "escenas.txt")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(texto)


if __name__ == "__main__":
    main()

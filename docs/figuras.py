"""Genera los diagramas del informe (docs/img/arquitectura.png, maquina_estados.png, ciclo_agente.png)."""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
AZUL, ROJO, VERDE, GRIS, AMARILLO = "#2f4b7c", "#c0392b", "#2e7d32", "#eceff4", "#f2c94c"


def caja(ax, x, y, w, h, texto, color=GRIS, borde=AZUL, size=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec=borde, lw=1.5))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=size)


def flecha(ax, p, q, texto="", rad=0.0, color="#333", size=7.5, off=(0, 0)):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=13, lw=1.3, color=color,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2))
    if texto:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], texto, fontsize=size,
                ha="center", va="center", color=color,
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.8))


def lienzo(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w), ax.set_ylim(0, h), ax.axis("off")
    return fig, ax


def arquitectura():
    fig, ax = lienzo(9, 6)
    capas = [("game/  (UI Pygame, única capa con pygame)", 5.0, "#dfe9f7"),
             ("sim/  Simulation, contract.py, mapgen.py, fake_sim.py", 3.85, "#e8f3e8"),
             ("agents/  guard.py · camara.py · perception.py · memory.py · bus.py", 2.7, "#fdf1d6"),
             ("core/  graph.py · pathfinding.py (Dijkstra, A*) · recursion.py (DFS limitado)", 1.55, "#f6dede")]
    for texto, y, c in capas:
        caja(ax, 0.4, y, 8.2, 0.85, texto, color=c, size=10)
    for y in (5.0, 3.85, 2.7):
        flecha(ax, (4.5, y), (4.5, y - 0.3), "usa", size=8)
    caja(ax, 0.4, 0.3, 4.0, 0.75, "bench/  benchmarks (sin ventana)", size=9)
    caja(ax, 4.6, 0.3, 4.0, 0.75, "tests/  pytest (13 pruebas)", size=9)
    ax.text(4.5, 5.95, "Arquitectura por capas (cada capa solo conoce a la de abajo)", ha="center",
            fontsize=11, weight="bold")
    fig.savefig(os.path.join(IMG, "arquitectura.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def _borde(c, t, w=2.0, h=0.7):
    """Punto del borde de la caja centrada en c, en dirección hacia t."""
    dx, dy = t[0] - c[0], t[1] - c[1]
    k = min((w / 2) / abs(dx) if dx else 1e9, (h / 2) / abs(dy) if dy else 1e9)
    return (c[0] + dx * k, c[1] + dy * k)


def maquina_estados():
    fig, ax = lienzo(10, 6.2)
    pos = {"PATRULLA": (1.5, 4.8), "INVESTIGAR": (5.0, 4.8), "BUSCAR": (8.5, 4.8),
           "VOLVER_A_PATRULLA": (1.5, 1.6), "ALERTA": (5.0, 1.6)}
    col = {"PATRULLA": "#e8f3e8", "INVESTIGAR": "#fdf1d6", "BUSCAR": "#fdf1d6", "ALERTA": "#f6dede",
           "VOLVER_A_PATRULLA": "#dfe9f7"}
    for n, (x, y) in pos.items():
        caja(ax, x - 1.0, y - 0.35, 2.0, 0.7, n.replace("_A_", "\nA_"), col[n], size=9.5)

    def f(a, b, txt, rad=0.0, off=(0, 0), dy=0.0, color="#333"):
        p, q = _borde(pos[a], pos[b]), _borde(pos[b], pos[a])
        flecha(ax, (p[0], p[1] + dy), (q[0], q[1] + dy), txt, rad, color, off=off)

    f("PATRULLA", "INVESTIGAR", "evidencia nueva\n(ruido, mensaje,\nfalsa alarma)", off=(0, 0.62), dy=0.12)
    f("INVESTIGAR", "BUSCAR", "llega al objetivo", off=(0, 0.3), dy=0.12)
    f("BUSCAR", "INVESTIGAR", "evidencia más\nreciente", off=(0, -0.45), dy=-0.12)
    f("INVESTIGAR", "VOLVER_A_PATRULLA", "evidencia caducó\n(TTL)", off=(0.15, 0.0))
    f("BUSCAR", "VOLVER_A_PATRULLA", "evidencia caducó (TTL)", rad=-0.28, off=(1.2, -1.1))
    f("VOLVER_A_PATRULLA", "PATRULLA", "llega al\nwaypoint", off=(-0.7, 0))
    f("ALERTA", "INVESTIGAR", "pierde de vista\n(hay evidencia)", off=(0.95, 0))
    f("ALERTA", "VOLVER_A_PATRULLA", "pierde de vista\n(sin evidencia)", off=(0, 0.45))
    ax.text(8.5, 1.6, "Desde cualquier estado,\nsi el guardia VE a Nox\n→ ALERTA (persecución)", fontsize=8.5,
            color=ROJO, ha="center", va="center", bbox=dict(fc="white", ec=ROJO, boxstyle="round"))
    flecha(ax, (7.0, 1.6), (6.05, 1.6), "", color=ROJO)
    ax.text(5, 6.05, "Máquina de estados del guardia (agents/guard.py, Guardia._decidir)", ha="center",
            fontsize=11, weight="bold")
    fig.savefig(os.path.join(IMG, "maquina_estados.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def ciclo():
    fig, ax = lienzo(10, 5)
    pasos = [("1. Percepción", "cono + Bresenham,\nruido, mensajes"), ("2. Memoria", "evidencias (pos, tick)\ncon TTL"),
             ("3. Decisión", "estado y objetivo\n(máquina de estados)"), ("4. Planificación", "Dijkstra / A*\n(replanifica)"),
             ("5. Ejecución", "mover 1 casilla\n(velocidad por estado)"), ("6. Evaluación", "¿plan válido?\nactualiza visitas")]
    xs = [0.2, 3.5, 6.8, 6.8, 3.5, 0.2]
    ys = [3.2, 3.2, 3.2, 0.9, 0.9, 0.9]
    for (t, d), x, y in zip(pasos, xs, ys):
        caja(ax, x, y, 2.9, 1.2, f"{t}\n{d}", "#dfe9f7", size=9)
    flecha(ax, (3.1, 3.8), (3.5, 3.8)), flecha(ax, (6.4, 3.8), (6.8, 3.8))
    flecha(ax, (8.25, 3.2), (8.25, 2.1))
    flecha(ax, (6.8, 1.5), (6.4, 1.5)), flecha(ax, (3.5, 1.5), (3.1, 1.5))
    flecha(ax, (1.65, 2.1), (1.65, 3.2), "vuelve al\nsiguiente tick")
    caja(ax, 3.5, 2.35, 2.9, 0.55, "Bus de mensajes (agents/bus.py)", "#fdf1d6", size=8.5)
    ax.text(5, 4.85, "Ciclo del agente guardia (Guardia.paso, cada tick)", ha="center", fontsize=11, weight="bold")
    fig.savefig(os.path.join(IMG, "ciclo_agente.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    arquitectura(), maquina_estados(), ciclo()
    print("Diagramas generados en", IMG)

"""La recursión termina por el límite de profundidad."""
from core.graph import Mapa, construir_grafo
from core.recursion import rutas_dfs


def _abierto(n):
    return construir_grafo(Mapa.desde_ascii(["." * n] * n))


def test_termina_por_limite():
    g = _abierto(30)
    for d in (0, 1, 3, 5):
        rutas, llamadas = rutas_dfs(g, (15, 15), d)
        assert all(len(r) <= d + 1 for r in rutas)        # nunca pasa del límite
        assert all(len(set(r)) == len(r) for r in rutas)  # rutas simples
        assert llamadas <= 1 + sum(4 * 3 ** k for k in range(d))  # cota b^d
    assert rutas_dfs(g, (15, 15), 0)[0] == [[(15, 15)]]  # caso base inmediato


def test_termina_en_callejon_y_con_tope():
    g = construir_grafo(Mapa.desde_ascii(["....."]))
    rutas, _ = rutas_dfs(g, (0, 0), 100)   # límite enorme, pero el pasillo se acaba
    assert rutas == [[(i, 0) for i in range(5)]]
    rutas, _ = rutas_dfs(_abierto(30), (15, 15), 12, max_rutas=50)
    assert len(rutas) <= 50

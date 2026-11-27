"""La simulación falsa respeta el contrato de la UI."""
from sim.contract import Accion, Snapshot
from sim.fake_sim import FakeSimulation


def test_fake_snapshot_y_acciones():
    sim = FakeSimulation()
    sim.step(Accion(mover="derecha"))
    sim.falsa_alarma((5, 5))
    sim.bloquear_puerta(0)
    snap = sim.snapshot()
    assert isinstance(snap, Snapshot)
    assert len(snap.guardias) == 2 and snap.mapa.puertas[0].estado == "bloqueada"

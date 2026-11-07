"""Evolução da incerteza média dos casos ativos."""
import pytest

from app.services.uncertainty_evolution import aggregate_uncertainty_evolution


def linha(caso, t, inc):
    return {"casoId": caso, "calculadoEm": t, "incerteza": inc}


def test_sem_dados_devolve_lista_vazia():
    assert aggregate_uncertainty_evolution([]) == []


def test_um_caso_acompanha_os_proprios_valores():
    pts = aggregate_uncertainty_evolution([
        linha("c1", "2026-01-01T10:00", 100.0),
        linha("c1", "2026-01-02T10:00", 60.0),
    ])
    assert [p["incerteza"] for p in pts] == [100.0, 60.0]
    assert all(p["casos"] == 1 for p in pts)


def test_media_usa_o_ultimo_valor_de_cada_caso():
    pts = aggregate_uncertainty_evolution([
        linha("c1", "2026-01-01T10:00", 100.0),
        linha("c2", "2026-01-02T10:00", 50.0),   # c2 entra: média (100 + 50) / 2
        linha("c1", "2026-01-03T10:00", 30.0),   # c1 cai para 30: média (30 + 50) / 2
    ])
    assert [(p["incerteza"], p["casos"]) for p in pts] == [(100.0, 1), (75.0, 2), (40.0, 2)]


def test_caso_sem_analise_ainda_nao_entra_na_media():
    pts = aggregate_uncertainty_evolution([linha("c1", "2026-01-01T10:00", 80.0)])
    assert pts[-1]["casos"] == 1


def test_ordem_cronologica_independente_da_entrada():
    pts = aggregate_uncertainty_evolution([
        linha("c1", "2026-01-03T10:00", 20.0),
        linha("c1", "2026-01-01T10:00", 90.0),
    ])
    assert [p["calculadoEm"] for p in pts] == ["2026-01-01T10:00", "2026-01-03T10:00"]


def test_limita_aos_pontos_mais_recentes():
    rows = [linha("c1", f"2026-01-{d:02d}T10:00", 100 - d) for d in range(1, 29)]
    pts = aggregate_uncertainty_evolution(rows, max_points=5)
    assert len(pts) == 5
    assert pts[-1]["calculadoEm"] == "2026-01-28T10:00"


def test_ignora_linhas_sem_valor():
    pts = aggregate_uncertainty_evolution([
        {"casoId": "c1", "calculadoEm": "2026-01-01T10:00", "incerteza": None},
        linha("c1", "2026-01-02T10:00", 40.0),
    ])
    assert len(pts) == 1 and pts[0]["incerteza"] == pytest.approx(40.0)

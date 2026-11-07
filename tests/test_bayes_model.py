"""Testes do modelo bayesiano (seção 16 da documentação).

Os valores esperados foram calculados à mão a partir de
C(Hi, ej) = 1 + r * v * 1/|S| e do posterior normalizado.
"""
import math

import pytest

from app.bayes.model import (
    BayesianNetwork,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Suspect,
    Trend,
)


def ev(id_, r, links, status=EvidenceStatus.COLETADA):
    return Evidence(id=id_, name=id_, type=EvidenceType.DNA, status=status,
                    reliability=r, suspect_links=links)


def suspects(n):
    return [Suspect(id=f"s{i}", name=f"S{i}") for i in range(1, n + 1)]


def by_id(result):
    return {r.suspect.id: r for r in result.ranking}


def test_prior_uniforme_sem_evidencias():
    res = BayesianNetwork().run("c", suspects(4), [])
    for r in res.ranking:
        assert r.p_h_given_e == pytest.approx(0.25)
        assert r.prior == pytest.approx(0.25)
    assert res.case_uncertainty == pytest.approx(75.0)


def test_posterior_soma_um():
    ss = suspects(3)
    evs = [ev("e1", 0.9, {"s1": 0.8, "s2": 0.3}), ev("e2", 0.5, {"s3": 0.6})]
    res = BayesianNetwork().run("c", ss, evs)
    assert res.sum_check() == pytest.approx(1.0)


def test_exemplo_da_documentacao_contribuicao_exclusiva():
    # r=0,90, v=0,95, um único suspeito -> C = 1 + 0,90*0,95*1 = 1,855
    net = BayesianNetwork()
    ss = suspects(2)
    e = ev("e", 0.90, {"s1": 0.95})
    assert net._evidence_contribution(ss[0], e, ss) == pytest.approx(1.855)


def test_exemplo_da_documentacao_contribuicao_compartilhada():
    # a mesma evidência dividida com outro suspeito -> C = 1 + 0,90*0,95*0,5 = 1,4275
    net = BayesianNetwork()
    ss = suspects(2)
    e = ev("e", 0.90, {"s1": 0.95, "s2": 0.95})
    assert net._evidence_contribution(ss[0], e, ss) == pytest.approx(1.4275)


def test_evidencia_exclusiva_posterior():
    # S1 tem C=1,855 e S2 não tem evidência (C=1): posterior = 1,855/2,855
    res = by_id(BayesianNetwork().run("c", suspects(2), [ev("e", 0.90, {"s1": 0.95})]))
    assert res["s1"].p_h_given_e == pytest.approx(1.855 / 2.855)
    assert res["s2"].p_h_given_e == pytest.approx(1 / 2.855)
    assert res["s1"].position == 1


def test_evidencia_compartilhada_igualmente_nao_diferencia_suspeitos():
    res = by_id(BayesianNetwork().run("c", suspects(2), [ev("e", 0.9, {"s1": 0.95, "s2": 0.95})]))
    assert res["s1"].p_h_given_e == pytest.approx(0.5)
    assert res["s2"].p_h_given_e == pytest.approx(0.5)


def test_peso_de_vinculo_por_suspeito():
    # r=0,5; v1=0,8 e v2=0,4; |S|=2 -> C1=1,2 e C2=1,1
    res = by_id(BayesianNetwork().run("c", suspects(2), [ev("e", 0.5, {"s1": 0.8, "s2": 0.4})]))
    assert res["s1"].p_h_given_e == pytest.approx(1.2 / 2.3)
    assert res["s2"].p_h_given_e == pytest.approx(1.1 / 2.3)


def test_evidencia_nao_vinculada_nao_altera_o_ranking():
    base = by_id(BayesianNetwork().run("c", suspects(3), [ev("e1", 0.8, {"s1": 0.7})]))
    com = by_id(BayesianNetwork().run(
        "c", suspects(3), [ev("e1", 0.8, {"s1": 0.7}), ev("e2", 0.9, {"s9": 0.9})]))
    for k in base:
        assert com[k].p_h_given_e == pytest.approx(base[k].p_h_given_e)


def test_mais_evidencias_aumentam_a_probabilidade():
    uma = by_id(BayesianNetwork().run("c", suspects(2), [ev("e1", 0.8, {"s1": 0.8})]))
    duas = by_id(BayesianNetwork().run(
        "c", suspects(2), [ev("e1", 0.8, {"s1": 0.8}), ev("e2", 0.7, {"s1": 0.9})]))
    assert duas["s1"].p_h_given_e > uma["s1"].p_h_given_e


def test_estabilidade_numerica_com_muitas_evidencias():
    # 3000 evidências: o produto direto estouraria; em log-space continua válido
    evs = [ev(f"e{i}", 0.9, {"s1": 0.9}) for i in range(3000)]
    res = BayesianNetwork().run("c", suspects(3), evs)
    assert res.sum_check() == pytest.approx(1.0)
    assert not any(math.isnan(r.p_h_given_e) or math.isinf(r.p_h_given_e) for r in res.ranking)
    assert by_id(res)["s1"].p_h_given_e == pytest.approx(1.0)


def test_sem_suspeitos_levanta_erro():
    with pytest.raises(ValueError):
        BayesianNetwork().run("c", [], [])


def test_atributos_de_perfil_nao_alteram_o_resultado():
    a = Suspect(id="s1", name="A", behavior=10, aggressiveness=10, proximity=10,
                social_connections=10, confession_level=10, crime_before="Sim", non_compliance="Sim")
    b = Suspect(id="s2", name="B", behavior=99, aggressiveness=99, proximity=99,
                social_connections=99, confession_level=99, crime_before="Não", non_compliance="Não")
    res = by_id(BayesianNetwork().run("c", [a, b], []))
    assert res["s1"].p_h_given_e == pytest.approx(0.5)
    assert res["s2"].p_h_given_e == pytest.approx(0.5)


@pytest.mark.parametrize("atual,esperado", [
    (50.4, Trend.STABLE),   # variação de 0,4 p.p. (< limiar 0,5)
    (50.5, Trend.STABLE),   # exatamente no limiar: ainda estável
    (50.6, Trend.UP),
    (49.4, Trend.DOWN),
])
def test_tendencia_limiar_de_meio_ponto(atual, esperado):
    assert BayesianNetwork._compute_trend("s1", atual, {"s1": 50.0}) == esperado


def test_tendencia_sem_analise_anterior_e_estavel():
    assert BayesianNetwork._compute_trend("s1", 70.0, {}) == Trend.STABLE


def test_tendencia_entra_no_resultado():
    ss = suspects(2)
    anterior = BayesianNetwork().run("c", ss, [])
    res = BayesianNetwork().run("c", ss, [ev("e", 0.9, {"s1": 0.95})],
                                previous_results=anterior.ranking)
    r = by_id(res)
    assert r["s1"].trend == Trend.UP
    assert r["s2"].trend == Trend.DOWN

"""A explicação da tela de Análise Probabilística tem que bater com o cálculo."""
import math

import pytest

from app.bayes.model import (
    BayesianNetwork,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Suspect,
    evidence_contribution,
)


def ev(id_, r, links):
    return Evidence(id=id_, name=id_, type=EvidenceType.DNA, status=EvidenceStatus.COLETADA,
                    reliability=r, suspect_links=links)


def test_exemplos_da_documentacao():
    assert evidence_contribution(0.90, 0.95, 1) == pytest.approx(1.855)
    assert evidence_contribution(0.90, 0.95, 2) == pytest.approx(1.4275)


def test_sem_suspeitos_ligados_nao_divide_por_zero():
    assert evidence_contribution(0.5, 0.5, 0) == pytest.approx(1.25)


def test_produto_das_contribuicoes_e_o_score_do_modelo():
    # a tela mostra "c1 × c2 = P(E|H)": o produto precisa ser exatamente o P(E|H) do modelo
    ss = [Suspect(id="s1", name="S1"), Suspect(id="s2", name="S2"), Suspect(id="s3", name="S3")]
    evs = [
        ev("e1", 0.9, {"s1": 0.8, "s2": 0.4}),   # compartilhada
        ev("e2", 0.7, {"s1": 0.6}),              # exclusiva
    ]
    res = {r.suspect.id: r for r in BayesianNetwork().run("c", ss, evs).ranking}

    for sid in ("s1", "s2", "s3"):
        produto = math.prod(
            evidence_contribution(e.reliability, e.suspect_links[sid], len(e.suspect_links))
            for e in evs if sid in e.suspect_links
        )
        assert produto == pytest.approx(res[sid].p_e_given_h)


def test_suspeito_sem_evidencia_tem_score_neutro_mas_posterior_diferente_do_prior():
    # o texto da tela: sem evidências P(E|H)=1 e o numerador é o prior, mas a
    # probabilidade final só é igual ao prior se NENHUM suspeito tiver evidências.
    ss = [Suspect(id="s1", name="S1"), Suspect(id="s2", name="S2"), Suspect(id="s3", name="S3")]
    com = {r.suspect.id: r for r in BayesianNetwork().run("c", ss, [ev("e1", 0.9, {"s1": 0.8})]).ranking}
    assert com["s3"].p_e_given_h == pytest.approx(1.0)
    assert com["s3"].numerator == pytest.approx(com["s3"].prior)
    assert com["s3"].p_h_given_e < com["s3"].prior      # caiu: outro suspeito tem evidência

    sem = {r.suspect.id: r for r in BayesianNetwork().run("c", ss, []).ranking}
    assert sem["s3"].p_h_given_e == pytest.approx(sem["s3"].prior)  # aqui sim, igual ao prior

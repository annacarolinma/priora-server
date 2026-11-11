"""Evidência que inocenta (álibi, contradição): contribuição menor que 1."""
import pytest
from pydantic import ValidationError

from app.bayes.model import (
    BayesianNetwork,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    Suspect,
    evidence_contribution,
)
from app.schemas.evidence_schema import VinculoInput


def _ev(eid, r, links, effects=None):
    return Evidence(
        id=eid, name=eid, type=EvidenceType.OUTRA, status=EvidenceStatus.COLETADA,
        reliability=r, suspect_links=links, suspect_effects=effects or {},
    )


def _rank(evs, ids=("A", "B", "C")):
    suspects = [Suspect(id=i, name=i) for i in ids]
    return {x.suspect.id: x.probability_pct for x in BayesianNetwork().run("c", suspects, evs).ranking}


def test_formula_de_quem_incrimina_nao_mudou():
    assert evidence_contribution(0.8, 0.5, 2) == pytest.approx(1 + 0.8 * 0.5 / 2)
    assert evidence_contribution(0.8, 0.5, 1, "Incrimina") == pytest.approx(1.4)


def test_quem_inocenta_e_menor_que_1_e_simetrico():
    c_inocenta = evidence_contribution(0.8, 0.5, 1, "Inocenta")
    assert c_inocenta == pytest.approx(1 / 1.4)
    assert c_inocenta < 1
    # uma evidência que incrimina e outra que inocenta, com os mesmos r e v, se anulam
    assert c_inocenta * evidence_contribution(0.8, 0.5, 1, "Incrimina") == pytest.approx(
        1.0 / 1.4 * 1.4
    )


def test_efeito_omitido_equivale_a_incrimina():
    sem = _rank([_ev("e1", 0.7, {"A": 0.6}), _ev("e2", 0.5, {"B": 0.4})])
    com = _rank([
        _ev("e1", 0.7, {"A": 0.6}, {"A": "Incrimina"}),
        _ev("e2", 0.5, {"B": 0.4}, {"B": "Incrimina"}),
    ])
    assert sem == pytest.approx(com)


def test_alibi_reduz_a_probabilidade_do_suspeito():
    base = _rank([_ev("e1", 0.7, {"A": 0.7}), _ev("e2", 0.5, {"B": 0.4})])
    com_alibi = _rank([
        _ev("e1", 0.7, {"A": 0.7}), _ev("e2", 0.5, {"B": 0.4}),
        _ev("alibi", 0.9, {"A": 0.9}, {"A": "Inocenta"}),
    ])
    assert com_alibi["A"] < base["A"]
    assert com_alibi["B"] > base["B"]
    assert sum(com_alibi.values()) == pytest.approx(100.0)


def test_alibi_forte_inverte_o_lider():
    evs = [_ev("e1", 0.7, {"A": 0.7}), _ev("e2", 0.5, {"B": 0.4})]
    assert _rank(evs)["A"] > _rank(evs)["B"]
    evs.append(_ev("alibi", 0.9, {"A": 0.9}, {"A": "Inocenta"}))
    evs.append(_ev("alibi2", 0.9, {"A": 0.9}, {"A": "Inocenta"}))
    r = _rank(evs)
    assert r["B"] > r["A"]


def test_evidencia_fraca_nao_vence_a_forte_so_pela_quantidade_se_ha_contradicao():
    """O problema que motivou a mudança: muitas evidências fracas somavam sempre a favor."""
    fortissima = [_ev("f", 0.9, {"A": 0.9})]
    fracas = [_ev(f"w{i}", 0.3, {"B": 0.3}) for i in range(8)]
    sem_contradicao = _rank(fortissima + fracas, ids=("A", "B"))
    assert sem_contradicao["B"] > sem_contradicao["A"]  # limitação conhecida do modelo sem contradições
    # um álibi do B (contradição confiável) desfaz a vantagem acumulada
    com_contradicao = _rank(
        fortissima + fracas + [_ev("alibi", 0.9, {"B": 0.9}, {"B": "Inocenta"})], ids=("A", "B")
    )
    assert com_contradicao["A"] > com_contradicao["B"]


def test_fator_de_exclusividade_conta_so_quem_e_incriminado():
    # evidência que incrimina A e inocenta B: A não divide o efeito com B
    e = _ev("e", 0.8, {"A": 0.5, "B": 0.5}, {"A": "Incrimina", "B": "Inocenta"})
    assert e.n_incriminated == 1
    r = _rank([e], ids=("A", "B"))
    assert r["A"] > r["B"]


def test_schema_efeito_padrao_e_validacao():
    assert VinculoInput(suspeitoId="s", pesoVinculo=0.5).efeito == "Incrimina"
    assert VinculoInput(suspeitoId="s", pesoVinculo=0.5, efeito="Inocenta").efeito == "Inocenta"
    with pytest.raises(ValidationError):
        VinculoInput(suspeitoId="s", pesoVinculo=0.5, efeito="Talvez")

"""Tipos de evidência: novos tipos padrão e tipo personalizado ("Outra")."""
import pytest
from pydantic import ValidationError

from app.bayes.model import EvidenceType, evidence_type
from app.schemas.evidence_schema import (
    CreateEvidenceRequest,
    UpdateEvidenceRequest,
    TIPO_MAX,
)


def _criar(tipo):
    return CreateEvidenceRequest(
        casoId="c", vinculos=[{"suspeitoId": "s", "pesoVinculo": 0.5}],
        nome="x", tipo=tipo, dataColeta="2026-01-01", peso=0.5,
    )


@pytest.mark.parametrize("tipo", ["Motivação", "Antecedente", "Pericial", "Telefônica", "Comportamento", "DNA"])
def test_tipos_padrao_aceitos(tipo):
    assert _criar(tipo).tipo == tipo


def test_tipo_personalizado_aceito_e_normalizado():
    assert _criar("  Registro   bancário ").tipo == "Registro bancário"


@pytest.mark.parametrize("tipo", ["", "   ", "a" * (TIPO_MAX + 1)])
def test_tipo_vazio_ou_longo_demais_recusado(tipo):
    with pytest.raises(ValidationError):
        _criar(tipo)


def test_edicao_valida_o_tipo_quando_enviado():
    assert UpdateEvidenceRequest().tipo is None
    assert UpdateEvidenceRequest(tipo="Cadeia de custódia").tipo == "Cadeia de custódia"
    with pytest.raises(ValidationError):
        UpdateEvidenceRequest(tipo="  ")


def test_motor_bayesiano_nao_quebra_com_tipo_personalizado():
    assert evidence_type("Telefônica") is EvidenceType.TELEFONICA
    assert evidence_type("Registro bancário") is EvidenceType.OUTRA

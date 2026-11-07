"""Peso da evidência e peso de vínculo: sempre 0 < x < 1 (nunca 0% nem 100%)."""
import pytest
from pydantic import ValidationError

from app.schemas.evidence_schema import CreateEvidenceRequest, UpdateEvidenceRequest


def criar(peso, vinculo):
    return CreateEvidenceRequest(
        casoId="c", nome="x", tipo="DNA", dataColeta="2026-01-01", peso=peso,
        vinculos=[{"suspeitoId": "s1", "pesoVinculo": vinculo}],
    )


@pytest.mark.parametrize("peso,vinculo", [(0.01, 0.99), (0.5, 0.5), (0.99, 0.01)])
def test_pesos_validos(peso, vinculo):
    criar(peso, vinculo)


@pytest.mark.parametrize("peso,vinculo", [
    (0, 0.5), (1, 0.5), (0.5, 0), (0.5, 1), (-0.1, 0.5), (1.2, 0.5), (0.5, -1), (0.5, 2),
])
def test_pesos_invalidos(peso, vinculo):
    with pytest.raises(ValidationError):
        criar(peso, vinculo)


@pytest.mark.parametrize("peso", [0, 1, -1, 2])
def test_edicao_rejeita_extremos(peso):
    with pytest.raises(ValidationError):
        UpdateEvidenceRequest(peso=peso)


def test_edicao_aceita_peso_valido_ou_ausente():
    UpdateEvidenceRequest(peso=0.3)
    UpdateEvidenceRequest()

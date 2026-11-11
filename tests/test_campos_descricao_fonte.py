"""Campos opcionais: descrição do suspeito (até 1000) e fonte da evidência (até 300)."""
import pytest
from pydantic import ValidationError

from app.schemas.evidence_schema import CreateEvidenceRequest, UpdateEvidenceRequest
from app.schemas.suspect_schema import CreateSuspectRequest, UpdateSuspectRequest

SUSPEITO = dict(
    casoId="c", nome="Ana", idade=30,
    historicoCriminal=50, caracteristicasCriminais=50, significanciaTempoLugar=50,
    coerenciaInterpessoal=50, conscienciaForense=50,
    crimeSimilarAntes="Não sei", histDescumprimento="Não sei",
)
EVIDENCIA = dict(
    casoId="c", vinculos=[{"suspeitoId": "s", "pesoVinculo": 0.5}], nome="Laudo",
    tipo="Documental", dataColeta="2026-01-01", peso=0.5,
)


def test_suspect_description_is_optional():
    assert CreateSuspectRequest(**SUSPEITO).descricao is None
    assert UpdateSuspectRequest(**{k: v for k, v in SUSPEITO.items() if k != "casoId"}).descricao is None


def test_suspect_description_limit():
    assert CreateSuspectRequest(**SUSPEITO, descricao="a" * 1000).descricao
    with pytest.raises(ValidationError):
        CreateSuspectRequest(**SUSPEITO, descricao="a" * 1001)


def test_evidence_source_is_optional_and_limited():
    assert CreateEvidenceRequest(**EVIDENCIA).fonte is None
    assert CreateEvidenceRequest(**EVIDENCIA, fonte="a" * 300).fonte
    with pytest.raises(ValidationError):
        CreateEvidenceRequest(**EVIDENCIA, fonte="a" * 301)
    with pytest.raises(ValidationError):
        UpdateEvidenceRequest(fonte="a" * 301)

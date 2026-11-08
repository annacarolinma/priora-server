"""Situação do caso: Ativo, Pendente ou Finalizado (nomes antigos são convertidos)."""
import pytest
from pydantic import ValidationError

from app.schemas.case_schema import CreateCaseRequest, UpdateCaseRequest

CREATE = {"userId": "u", "nome": "C", "descricao": "d", "prioridade": "Alta"}
UPDATE = {"nome": "C", "descricao": "d", "prioridade": "Alta", "dataOcorrencia": "2026-01-01"}


@pytest.mark.parametrize("status", ["Ativo", "Pendente", "Finalizado"])
def test_valid_status(status):
    assert CreateCaseRequest(**CREATE, status=status).status == status
    assert UpdateCaseRequest(**UPDATE, status=status).status == status


@pytest.mark.parametrize("old,new", [("Arquivado", "Pendente"), ("Concluído", "Finalizado")])
def test_legacy_names_are_converted(old, new):
    assert CreateCaseRequest(**CREATE, status=old).status == new
    assert UpdateCaseRequest(**UPDATE, status=old).status == new


def test_unknown_status_is_rejected():
    with pytest.raises(ValidationError):
        CreateCaseRequest(**CREATE, status="Qualquer coisa")
    with pytest.raises(ValidationError):
        UpdateCaseRequest(**UPDATE, status="")

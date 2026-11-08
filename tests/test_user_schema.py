"""Cargo do usuário: opcional, com limite de tamanho."""
import pytest
from pydantic import ValidationError

from app.schemas.user_schema import CARGO_MAX, UpdateUserRequest

BASE = {"primeiroNome": "Ana", "sobrenome": "Silva", "email": "ana@exemplo.com"}


def test_cargo_ausente_vira_none():
    # None = manter o cargo atual (clientes antigos não apagam o cargo de ninguém)
    assert UpdateUserRequest(**BASE).cargo is None


@pytest.mark.parametrize("cargo", ["", "Delegada", "x" * CARGO_MAX])
def test_cargo_valido(cargo):
    assert UpdateUserRequest(**BASE, cargo=cargo).cargo == cargo


def test_cargo_longo_demais():
    with pytest.raises(ValidationError):
        UpdateUserRequest(**BASE, cargo="x" * (CARGO_MAX + 1))

"""Redefinição de senha: token inválido/expirado/usado deve dar erro (não 200)."""
from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from app.services import user_service


@contextmanager
def fake_session():
    yield object()


def test_token_invalido_levanta_400(monkeypatch):
    monkeypatch.setattr(user_service, "get_session", fake_session)
    monkeypatch.setattr(user_service, "reset_password", lambda tx, token, h: None)
    with pytest.raises(HTTPException) as exc:
        user_service.reset_password_service("inventado", "NovaSenha123!")
    assert exc.value.status_code == 400


def test_token_valido_confirma(monkeypatch):
    monkeypatch.setattr(user_service, "get_session", fake_session)
    monkeypatch.setattr(user_service, "reset_password", lambda tx, token, h: {"id": "u1"})
    assert user_service.reset_password_service("ok", "NovaSenha123!") == {"message": "Senha atualizada"}


def test_senha_nova_e_guardada_como_hash(monkeypatch):
    guardado = {}

    def capturar(tx, token, senha_hash):
        guardado["hash"] = senha_hash
        return {"id": "u1"}

    monkeypatch.setattr(user_service, "get_session", fake_session)
    monkeypatch.setattr(user_service, "reset_password", capturar)
    user_service.reset_password_service("ok", "NovaSenha123!")
    assert guardado["hash"].startswith("$2") and "NovaSenha123!" not in guardado["hash"]

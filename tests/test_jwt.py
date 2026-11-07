"""Duração e validação do token de login."""
import time

import pytest
from jose import JWTError, jwt

from app.utils import jwt as jwt_utils


def test_token_dura_12_horas_por_padrao():
    token = jwt_utils.create_access_token({"sub": "u1"})
    payload = jwt_utils.decode_access_token(token)
    restante = payload["exp"] - time.time()
    assert 11.9 * 3600 < restante <= 12 * 3600


def test_token_expirado_e_rejeitado(monkeypatch):
    monkeypatch.setattr(jwt_utils, "ACCESS_TOKEN_EXPIRE_HOURS", -1)
    token = jwt_utils.create_access_token({"sub": "u1"})
    with pytest.raises(JWTError):
        jwt_utils.decode_access_token(token)


def test_token_com_outra_chave_e_rejeitado():
    falso = jwt.encode({"sub": "u1", "exp": time.time() + 3600}, "outra-chave", algorithm="HS256")
    with pytest.raises(JWTError):
        jwt_utils.decode_access_token(falso)

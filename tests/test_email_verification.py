"""Confirmação de e-mail: token, exigência configurável e bloqueio no login."""
import asyncio

import bcrypt
import pytest
from fastapi import HTTPException

from app.core import email_verification as ev
from app.core.rate_limit import Cooldown
from app.services import user_service


def test_token_e_hash():
    t1, t2 = ev.new_token(), ev.new_token()
    assert t1 != t2 and len(t1) >= 40
    assert ev.hash_token(t1) == ev.hash_token(t1)
    assert ev.hash_token(t1) != t1
    assert ev.hash_token(t1) != ev.hash_token(t2)


@pytest.mark.parametrize("valor,esperado", [
    (None, True), ("true", True), ("1", True), ("false", False), ("FALSE", False), ("0", False), ("off", False),
])
def test_exigencia_configuravel(monkeypatch, valor, esperado):
    if valor is None:
        monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)
    else:
        monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", valor)
    assert ev.verification_required() is esperado


def test_horas_invalidas_voltam_ao_padrao(monkeypatch):
    monkeypatch.setenv("EMAIL_VERIFY_HOURS", "abc")
    assert ev.verification_hours() == 24
    monkeypatch.setenv("EMAIL_VERIFY_HOURS", "2")
    assert ev.verification_hours() == 2


def test_cooldown_de_reenvio():
    c = Cooldown(60)
    assert c.try_acquire("a@b.c") == 0
    assert c.try_acquire("a@b.c") > 0
    assert c.try_acquire("outro@b.c") == 0


class _Sessao:
    def __enter__(self):
        return object()

    def __exit__(self, *a):
        return False


def _login(monkeypatch, user, exigir=True):
    monkeypatch.setattr(user_service, "get_session", lambda: _Sessao())
    monkeypatch.setattr(user_service, "login_user", lambda tx, email: dict(user))
    monkeypatch.setattr(user_service, "verification_required", lambda: exigir)
    user_service.login_limiter.reset("t@x.com")


def _usuario(**extra):
    return {
        "id": "u1", "email": "t@x.com", "primeiroNome": "T", "sobrenome": "X",
        "senhaHash": bcrypt.hashpw(b"Senha123!", bcrypt.gensalt()).decode(), **extra,
    }


def test_login_bloqueado_ate_confirmar(monkeypatch):
    _login(monkeypatch, _usuario(emailVerificado=False))
    with pytest.raises(HTTPException) as e:
        user_service.login_user_service("t@x.com", "Senha123!")
    assert e.value.status_code == 403
    assert e.value.detail["code"] == "email_nao_confirmado"


def test_senha_errada_nao_revela_que_a_conta_esta_pendente(monkeypatch):
    _login(monkeypatch, _usuario(emailVerificado=False))
    with pytest.raises(HTTPException) as e:
        user_service.login_user_service("t@x.com", "errada")
    assert e.value.status_code == 401


@pytest.mark.parametrize("extra", [{"emailVerificado": True}, {}])
def test_conta_confirmada_ou_antiga_entra(monkeypatch, extra):
    _login(monkeypatch, _usuario(**extra))
    r = user_service.login_user_service("t@x.com", "Senha123!")
    assert r["token"] and "senhaHash" not in r["user"]


def test_com_exigencia_desligada_pendente_tambem_entra(monkeypatch):
    _login(monkeypatch, _usuario(emailVerificado=False), exigir=False)
    assert user_service.login_user_service("t@x.com", "Senha123!")["token"]


def test_cadastro_guarda_so_o_hash_e_envia_o_token(monkeypatch):
    guardado, enviado = {}, {}

    def fake_create(tx, email, pn, sn, senha_hash, email_verificado, token_hash, expira_horas):
        guardado.update(verificado=email_verificado, token_hash=token_hash)
        return {"id": "u1", "email": email}

    async def fake_send(email, nome, token, horas):
        enviado["token"] = token

    monkeypatch.setattr(user_service, "get_session", lambda: _Sessao())
    monkeypatch.setattr(user_service, "create_user", fake_create)
    monkeypatch.setattr(user_service, "send_verification_email", fake_send)
    monkeypatch.setattr(user_service, "verification_required", lambda: True)

    r = asyncio.run(user_service.create_user_service("a@b.c", "A", "B", "Senha123!"))
    assert r["verificacaoNecessaria"] and r["emailEnviado"]
    assert guardado["verificado"] is False
    assert guardado["token_hash"] == ev.hash_token(enviado["token"]) != enviado["token"]


def test_cadastro_sobrevive_a_falha_no_envio(monkeypatch):
    async def quebra(*a):
        raise RuntimeError("smtp fora")

    monkeypatch.setattr(user_service, "get_session", lambda: _Sessao())
    monkeypatch.setattr(user_service, "create_user", lambda *a, **k: {"id": "u1"})
    monkeypatch.setattr(user_service, "send_verification_email", quebra)
    monkeypatch.setattr(user_service, "verification_required", lambda: True)

    r = asyncio.run(user_service.create_user_service("a@b.c", "A", "B", "Senha123!"))
    assert r["verificacaoNecessaria"] and r["emailEnviado"] is False


def test_cadastro_sem_exigencia_ja_nasce_confirmado(monkeypatch):
    visto = {}

    def fake_create(tx, email, pn, sn, senha_hash, email_verificado, token_hash, expira_horas):
        visto.update(verificado=email_verificado, token_hash=token_hash)
        return {"id": "u1"}

    monkeypatch.setattr(user_service, "get_session", lambda: _Sessao())
    monkeypatch.setattr(user_service, "create_user", fake_create)
    monkeypatch.setattr(user_service, "verification_required", lambda: False)

    r = asyncio.run(user_service.create_user_service("a@b.c", "A", "B", "Senha123!"))
    assert visto == {"verificado": True, "token_hash": None}
    assert r["verificacaoNecessaria"] is False


def test_token_invalido_ou_expirado(monkeypatch):
    monkeypatch.setattr(user_service, "get_session", lambda: _Sessao())
    monkeypatch.setattr(user_service, "verify_email", lambda tx, h: None)
    with pytest.raises(HTTPException) as e:
        user_service.verify_email_service("qualquer")
    assert e.value.status_code == 400


def test_reenvio_nao_revela_se_a_conta_existe(monkeypatch):
    monkeypatch.setattr(user_service, "get_session", lambda: _Sessao())
    monkeypatch.setattr(user_service, "set_verification_token", lambda *a: None)
    user_service.verification_cooldown._last.clear()
    r = asyncio.run(user_service.resend_verification_service("naoexiste@x.com"))
    assert "message" in r
    with pytest.raises(HTTPException) as e:  # segundo pedido imediato cai no intervalo mínimo
        asyncio.run(user_service.resend_verification_service("naoexiste@x.com"))
    assert e.value.status_code == 429

"""
Confirmação de e-mail no cadastro.

O token enviado por e-mail é aleatório (secrets.token_urlsafe) e só o hash
SHA-256 dele é guardado no banco: quem ler o banco não consegue usar o link.

REQUIRE_EMAIL_VERIFICATION liga/desliga a exigência (padrão: ligada). Em
ambientes sem servidor de e-mail (ex.: Docker local da banca) ela fica
desligada e as contas nascem já confirmadas.
Contas antigas não têm a propriedade emailVerificado; só `false` bloqueia o
login, então elas continuam funcionando sem migração.
"""

import hashlib
import os
import secrets


def verification_required() -> bool:
    return os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "nao",
        "não",
        "off",
    )


def verification_hours() -> int:
    try:
        return max(1, int(os.getenv("EMAIL_VERIFY_HOURS", "24")))
    except ValueError:
        return 24


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()

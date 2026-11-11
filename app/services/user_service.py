from app.database.neo4j import get_session
from app.utils.jwt import create_access_token,decode_access_token
from fastapi import HTTPException
from app.core.rate_limit import login_limiter, verification_cooldown
from app.core.email_verification import (
    verification_required,
    verification_hours,
    new_token,
    hash_token,
)
import logging
from app.database.supabase_storage import upload_user_photo
from app.utils.email import send_recovery_email, send_verification_email
from app.repositories.user_repository import (
    create_user,
    verify_email,
    set_verification_token,
    login_user,
    set_recovery_token,
    reset_password,
    check_email_exists,
    get_user_by_id,
    update_user,
    get_user_password,
    update_user_password,
    update_user_photo,
)
import bcrypt
import secrets

logger = logging.getLogger("priora.users")



async def create_user_service(email, primeiro_nome, sobrenome, senha):
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    exigir = verification_required()
    token = new_token() if exigir else None
    horas = verification_hours()

    with get_session() as tx:
        user = create_user(
            tx, email, primeiro_nome, sobrenome, senha_hash,
            email_verificado=not exigir,
            token_hash=hash_token(token) if exigir else None,
            expira_horas=horas,
        )

    user = dict(user)
    user["verificacaoNecessaria"] = exigir
    user["emailEnviado"] = False

    if exigir:
        try:
            await send_verification_email(email, primeiro_nome, token, horas)
            user["emailEnviado"] = True
        except Exception:
            # a conta existe; a pessoa pode pedir o reenvio na tela
            logger.exception("Falha ao enviar o e-mail de confirmação para %s", email)

    return user


def verify_email_service(token):
    with get_session() as tx:
        ok = verify_email(tx, hash_token(token))

    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Link de confirmação inválido ou expirado. Peça um novo na tela de login.",
        )

    return {"message": "E-mail confirmado"}


async def resend_verification_service(email):
    """Resposta sempre igual, exista a conta ou não (não revela quais e-mails estão cadastrados)."""
    resposta = {"message": "Se a conta existir e estiver pendente, enviamos um novo link."}
    chave = (email or "").strip().lower()

    espera = verification_cooldown.try_acquire(chave)
    if espera:
        raise HTTPException(
            status_code=429,
            detail=f"Aguarde {espera} segundo(s) para pedir um novo e-mail.",
            headers={"Retry-After": str(espera)},
        )

    token = new_token()
    horas = verification_hours()
    with get_session() as tx:
        user = set_verification_token(tx, email, hash_token(token), horas)

    if user:
        try:
            await send_verification_email(email, user["primeiroNome"], token, horas)
        except Exception:
            logger.exception("Falha ao reenviar o e-mail de confirmação para %s", email)
            raise HTTPException(
                status_code=502,
                detail="Não foi possível enviar o e-mail agora. Tente de novo em instantes.",
            )

    return resposta


def login_user_service(email, senha):
    chave = (email or "").strip().lower()

    espera = login_limiter.retry_after(chave)
    if espera:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas de login. Tente novamente em {max(1, espera // 60)} minuto(s).",
            headers={"Retry-After": str(espera)},
        )

    with get_session() as tx:
        user = login_user(tx, email)

        if not user:
            login_limiter.register_failure(chave)
            raise HTTPException(
                status_code=401,
                detail="Email ou senha inválidos"
            )

        senha_correta = bcrypt.checkpw(
            senha.encode(),
            user["senhaHash"].encode()
        )

        if not senha_correta:
            login_limiter.register_failure(chave)
            raise HTTPException(
                status_code=401,
                detail="Email ou senha inválidos"
            )

        login_limiter.reset(chave)

        # contas antigas não têm a propriedade; só `false` bloqueia
        if user.get("emailVerificado") is False and verification_required():
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "email_nao_confirmado",
                    "message": "Confirme seu e-mail para entrar. Verifique sua caixa de entrada.",
                },
            )

        token = create_access_token({
            "sub": user["id"]
        })

        del user["senhaHash"]
        user.pop("emailVerificado", None)

        return {
            "user": user,
            "token": token
        }


async def recovery_token_service(email):
    token = secrets.token_urlsafe(32)

    with get_session() as tx:
        user = set_recovery_token(tx, email, token)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    await send_recovery_email(email, token)

    return {
        "message": "Email enviado"
    }


def reset_password_service(token, nova_senha):
    nova_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()

    with get_session() as tx:
        resultado = reset_password(tx, token, nova_hash)

    if not resultado:
        # token inexistente, já usado ou expirado: a senha NÃO foi alterada
        raise HTTPException(
            status_code=400,
            detail="Link de recuperação inválido ou expirado. Solicite um novo.",
        )

    return {"message": "Senha atualizada"}

def check_email_service(email):
    with get_session() as tx:
        exists = check_email_exists(tx, email)
    return {"exists": exists}

def get_current_user_service(token):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token inválido"
            )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado"
        )

    with get_session() as tx:
        user = get_user_by_id(tx, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    return user

def update_user_service(
    token,
    email,
    primeiro_nome,
    sobrenome,
    cargo=None
):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token inválido"
            )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado"
        )

    with get_session() as tx:

        user = update_user(
            tx,
            user_id,
            email,
            primeiro_nome,
            sobrenome,
            cargo
        )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    return user

async def upload_user_photo_service(user_id, file_bytes, content_type):
    url = await upload_user_photo(user_id, file_bytes, content_type)

    with get_session() as tx:
        user = update_user_photo(tx, user_id, url)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    return user


def change_password_service(
    token,
    senha_antiga,
    nova_senha
):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token inválido"
            )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado"
        )

    if len(nova_senha) < 8:
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve conter pelo menos 8 caracteres"
        )

    with get_session() as tx:

        senha_hash_atual = get_user_password(
            tx,
            user_id
        )

        if not senha_hash_atual:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )

        senha_correta = bcrypt.checkpw(
            senha_antiga.encode(),
            senha_hash_atual.encode()
        )

        if not senha_correta:
            raise HTTPException(
                status_code=400,
                detail="Senha antiga incorreta"
            )

        nova_hash = bcrypt.hashpw(
            nova_senha.encode(),
            bcrypt.gensalt()
        ).decode()

        update_user_password(
            tx,
            user_id,
            nova_hash
        )

    return {
        "message": "Senha alterada com sucesso"
    }
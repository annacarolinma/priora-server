from app.database.neo4j import get_session
from app.utils.jwt import create_access_token,decode_access_token
from fastapi import HTTPException
from app.core.rate_limit import login_limiter
from app.utils.email import send_recovery_email
from app.repositories.user_repository import (
    create_user,
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



def create_user_service(email, primeiro_nome, sobrenome, senha):
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    with get_session() as tx:
        return create_user(tx, email, primeiro_nome, sobrenome, senha_hash)


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

        token = create_access_token({
            "sub": user["id"]
        })

        del user["senhaHash"]

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
    sobrenome
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
            sobrenome
        )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado"
        )

    return user

def update_user_photo_service(token, foto_base64):
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

    if not foto_base64:
        raise HTTPException(
            status_code=400,
            detail="Imagem não enviada"
        )

    # Limita o tamanho da string Base64
    if len(foto_base64) > 5_000_000:
        raise HTTPException(
            status_code=400,
            detail="Imagem muito grande"
        )

    with get_session() as tx:
        user = update_user_photo(
            tx,
            user_id,
            foto_base64
        )

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
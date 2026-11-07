from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.core.security import get_current_user_id
from app.services.user_service import (
    create_user_service,
    login_user_service,
    recovery_token_service,
    reset_password_service,
    check_email_service,
    get_current_user_service,
    upload_user_photo_service,
    update_user_service,
    change_password_service,
)

from app.schemas.user_schema import (
    CreateUserRequest,
    LoginRequest,
    RecoverRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
    ChangePasswordRequest,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("/", status_code=201)
def create_user(data: CreateUserRequest):
    return create_user_service(
        data.email,
        data.primeiroNome,
        data.sobrenome,
        data.senha
    )

@router.post("/me/photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id),
):
    """Foto de perfil por upload de arquivo (antes era uma string base64 salva no Neo4j)."""
    file_bytes = await file.read()
    try:
        return await upload_user_photo_service(current_user_id, file_bytes, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(data: LoginRequest):
    return login_user_service(
        data.email,
        data.senha
    )


@router.post("/recover")
async def recover(data: RecoverRequest):
    return await recovery_token_service(data.email)


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest):
    return reset_password_service(
        data.token,
        data.novaSenha
    )


@router.get("/check-email")
def check_email(email: str):
    return check_email_service(email)


@router.get("/me")
def get_current_user(
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")

    return get_current_user_service(token)


@router.put("/me")
def update_current_user(
    data: UpdateUserRequest,
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")

    return update_user_service(
        token,
        data.email,
        data.primeiroNome,
        data.sobrenome
    )


@router.put("/me/password")
def change_password(
    data: ChangePasswordRequest,
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")

    return change_password_service(
        token,
        data.senhaAntiga,
        data.novaSenha
    )
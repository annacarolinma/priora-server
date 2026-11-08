from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# Tamanho máximo do cargo exibido no perfil (ex.: "Delegada de Polícia Civil")
CARGO_MAX = 60


class CreateUserRequest(BaseModel):
    email: EmailStr
    primeiroNome: str
    sobrenome: str
    senha: str


class LoginRequest(BaseModel):
    email: str
    senha: str


class RecoverRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    novaSenha: str

class UpdateUserRequest(BaseModel):
    primeiroNome: str
    sobrenome: str
    email: EmailStr
    # Opcional: ausente (None) mantém o cargo atual; "" remove o cargo.
    cargo: Optional[str] = Field(default=None, max_length=CARGO_MAX)


class ChangePasswordRequest(BaseModel):
    senhaAntiga: str
    novaSenha: str

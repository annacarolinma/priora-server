from pydantic import BaseModel, EmailStr


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


class ChangePasswordRequest(BaseModel):
    senhaAntiga: str
    novaSenha: str

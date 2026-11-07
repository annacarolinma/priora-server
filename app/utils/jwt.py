from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# Duração do login. Padrão de 12 h (um turno de trabalho); ajustável por
# JWT_EXPIRE_HOURS no .env. Antes eram 7 dias.
ACCESS_TOKEN_EXPIRE_HOURS = float(os.getenv("JWT_EXPIRE_HOURS", "12"))


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """
    Decodifica e valida um token JWT.
    Levanta jose.JWTError se o token for inválido, malformado ou expirado.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
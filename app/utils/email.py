from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import load_dotenv
import logging
import os

load_dotenv()

logger = logging.getLogger("priora.email")

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME") or "",
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD") or "",
    MAIL_FROM=os.getenv("MAIL_FROM") or "noreply@priora.local",
    MAIL_PORT=int(os.getenv("MAIL_PORT") or 587),
    MAIL_SERVER=os.getenv("MAIL_SERVER") or "localhost",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)


async def send_recovery_email(email: str, token: str):
    frontend_url = os.getenv("FRONTEND_URL")
    link = f"{frontend_url}/recover/new-password?token={token}"

    message = MessageSchema(
        subject="Recuperação de senha",
        recipients=[email],
        body=f"""
Clique no link abaixo para redefinir sua senha:

{link}
        """,
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)


async def send_verification_email(email: str, nome: str, token: str, hours: int):
    frontend_url = os.getenv("FRONTEND_URL")
    link = f"{frontend_url}/verify-email?token={token}"

    # Sem servidor de e-mail (dev/demonstração): o link vai para o log do servidor.
    if os.getenv("MAIL_SUPPRESS_SEND", "").strip().lower() in ("1", "true", "yes"):
        logger.warning("MAIL_SUPPRESS_SEND ativo. Link de confirmação de %s: %s", email, link)
        return

    message = MessageSchema(
        subject="Confirme seu e-mail - Priora",
        recipients=[email],
        body=f"""
Olá, {nome}!

Para ativar sua conta no Priora, confirme seu e-mail pelo link abaixo
(válido por {hours} horas):

{link}

Se você não criou uma conta, ignore esta mensagem.
        """,
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)


async def send_support_email(
    first_name: str,
    last_name: str,
    email: str,
    message_text: str
):
    support_email = os.getenv("SUPPORT_EMAIL")

    message = MessageSchema(
        subject=f"[Suporte] {first_name} {last_name}",
        recipients=[support_email],
        reply_to=[email],
        body=f"""
Nova mensagem recebida pelo formulário de contato.

Nome: {first_name} {last_name}
Email: {email}

Mensagem:
{message_text}
        """,
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
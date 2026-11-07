"""
Armazenamento de imagens (quadro investigativo, fotos de suspeitos e fotos de
perfil).

Tudo passa pelo backend: o navegador nunca fala direto com o Supabase e a
service_role key nunca sai daqui.

- Com SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY definidos, as imagens vão para
  buckets públicos do Supabase Storage (criados automaticamente se faltarem).
- Sem eles (ex.: implantação local/Docker), ficam em disco (UPLOAD_DIR) e são
  servidas pela própria API em /uploads.
"""
import os
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

SUPABASE_BOARD_BUCKET = os.getenv("SUPABASE_BOARD_BUCKET", "quadro-investigativo")
SUPABASE_SUSPECT_BUCKET = os.getenv("SUPABASE_SUSPECT_BUCKET", "suspect-photos")
SUPABASE_USER_BUCKET = os.getenv("SUPABASE_USER_BUCKET", "user-photos")

# Sem Supabase configurado, as imagens ficam em disco e são servidas em /uploads.
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000").rstrip("/")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB

_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def sniff_content_type(file_bytes: bytes) -> str | None:
    """Descobre o tipo real pelo conteúdo (o Content-Type enviado pelo cliente não é confiável)."""
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if file_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(file_bytes: bytes, content_type: str | None) -> tuple[str, str]:
    """Retorna (content_type real, extensão) ou levanta ValueError."""
    if not file_bytes:
        raise ValueError("Arquivo vazio.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError("Imagem muito grande (limite de 8 MB).")

    real_type = sniff_content_type(file_bytes)
    if real_type is None or real_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Tipo de arquivo não suportado. Envie JPEG, PNG, WEBP ou GIF.")

    return real_type, _EXTENSION_BY_CONTENT_TYPE[real_type]


async def _ensure_bucket(client: httpx.AsyncClient, bucket: str) -> None:
    await client.post(
        f"{SUPABASE_URL}/storage/v1/bucket",
        json={"id": bucket, "name": bucket, "public": True},
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
        },
    )


async def _store_image(
    bucket: str,
    local_folder: str,
    owner_id: str,
    file_bytes: bytes,
    content_type: str | None,
) -> str:
    """Valida e grava a imagem; devolve a URL pública."""
    real_type, extension = validate_image(file_bytes, content_type)
    filename = f"{uuid.uuid4()}.{extension}"

    if not USE_SUPABASE:
        folder = os.path.join(UPLOAD_DIR, local_folder, owner_id) if local_folder else os.path.join(UPLOAD_DIR, owner_id)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, filename), "wb") as f:
            f.write(file_bytes)
        prefix = f"{local_folder}/" if local_folder else ""
        return f"{PUBLIC_API_URL}/uploads/{prefix}{owner_id}/{filename}"

    object_path = f"{owner_id}/{filename}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": real_type,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(upload_url, content=file_bytes, headers=headers)

        # bucket ainda não existe: cria (público) e tenta de novo uma vez
        if response.status_code in (400, 404) and "bucket not found" in response.text.lower():
            await _ensure_bucket(client, bucket)
            response = await client.post(upload_url, content=file_bytes, headers=headers)

    if response.status_code not in (200, 201):
        raise Exception(f"Erro ao enviar imagem para o Supabase: {response.text}")

    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{object_path}"


async def upload_board_image(caso_id: str, file_bytes: bytes, content_type: str | None) -> str:
    # local_folder vazio mantém as URLs antigas (/uploads/<caso_id>/...)
    return await _store_image(SUPABASE_BOARD_BUCKET, "", caso_id, file_bytes, content_type)


async def upload_suspect_photo(caso_id: str, file_bytes: bytes, content_type: str | None) -> str:
    return await _store_image(SUPABASE_SUSPECT_BUCKET, "suspects", caso_id, file_bytes, content_type)


async def upload_user_photo(user_id: str, file_bytes: bytes, content_type: str | None) -> str:
    return await _store_image(SUPABASE_USER_BUCKET, "users", user_id, file_bytes, content_type)

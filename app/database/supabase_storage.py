import os
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BOARD_BUCKET = os.getenv("SUPABASE_BOARD_BUCKET", "quadro-investigativo")

# Sem Supabase configurado (ex.: implantação local/Docker), as imagens do
# quadro ficam em disco e são servidas pela própria API em /uploads.
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


async def upload_board_image(caso_id: str, file_bytes: bytes, content_type: str) -> str:
    """
    Envia a imagem para o Supabase Storage usando a service_role key
    (feito no backend de propósito — essa chave tem permissão total sobre o
    bucket e JAMAIS deve ir pro frontend/navegador).

    Retorna a URL pública da imagem já hospedada.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Tipo de arquivo não suportado. Envie JPEG, PNG, WEBP ou GIF.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError("Imagem muito grande (limite de 8 MB).")

    extension = _EXTENSION_BY_CONTENT_TYPE[content_type]
    object_path = f"{caso_id}/{uuid.uuid4()}.{extension}"

    if not USE_SUPABASE:
        local_path = os.path.join(UPLOAD_DIR, caso_id)
        os.makedirs(local_path, exist_ok=True)
        filename = f"{uuid.uuid4()}.{extension}"
        with open(os.path.join(local_path, filename), "wb") as f:
            f.write(file_bytes)
        return f"{PUBLIC_API_URL}/uploads/{caso_id}/{filename}"

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BOARD_BUCKET}/{object_path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            upload_url,
            content=file_bytes,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Content-Type": content_type,
            },
        )

    if response.status_code not in (200, 201):
        raise Exception(f"Erro ao enviar imagem para o Supabase: {response.text}")

    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BOARD_BUCKET}/{object_path}"


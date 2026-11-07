from app.core.authorization import require_case_role, WRITE_ROLES
from app.database.neo4j import get_session
from app.database.supabase_storage import (
    upload_board_image,
    upload_suspect_photo,
    upload_user_photo,
)


async def upload_board_image_service(caso_id: str, file_bytes: bytes, content_type: str) -> str:
    return await upload_board_image(caso_id, file_bytes, content_type)


async def upload_suspect_photo_service(
    current_user_id: str, caso_id: str, file_bytes: bytes, content_type: str | None
) -> dict:
    # só quem pode editar o caso envia fotos de suspeitos
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
    return {"url": await upload_suspect_photo(caso_id, file_bytes, content_type)}

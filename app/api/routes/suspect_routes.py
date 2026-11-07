from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from app.core.security import get_current_user_id
from app.schemas.suspect_schema import CreateSuspectRequest
from app.schemas.suspect_schema import UpdateSuspectRequest
from app.services.upload_service import upload_suspect_photo_service
from app.services.suspect_service import (
    create_suspect_service,
    list_suspects_service,
    update_suspect_ranking_service,
    update_suspect_service,
    delete_suspect_service
)

router = APIRouter(prefix="/suspects", tags=["Suspects"])


@router.post("/", status_code=201)
def create_suspect(data: CreateSuspectRequest, current_user_id: str = Depends(get_current_user_id)):
    return create_suspect_service(current_user_id, data.dict())


@router.post("/case/{caso_id}/photo", status_code=201)
async def upload_suspect_photo(
    caso_id: str,
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id),
):
    """Envia a foto de um suspeito do caso; devolve {"url": ...} para salvar no suspeito."""
    file_bytes = await file.read()
    try:
        return await upload_suspect_photo_service(
            current_user_id, caso_id, file_bytes, file.content_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/case/{caso_id}")
def list_suspects(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    return list_suspects_service(current_user_id, caso_id)


@router.patch("/case/{caso_id}/ranking")
def update_ranking(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    return update_suspect_ranking_service(current_user_id, caso_id)


@router.patch("/{suspect_id}")
def update_suspect_route(suspect_id: str, data: UpdateSuspectRequest, current_user_id: str = Depends(get_current_user_id)):
    return update_suspect_service(
        current_user_id,
        suspect_id,
        data.dict()
    )


@router.delete("/case/{caso_id}/{suspect_id}")
def delete_suspect_route(caso_id: str, suspect_id: str, current_user_id: str = Depends(get_current_user_id)):
    return delete_suspect_service(current_user_id, caso_id, suspect_id)
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import traceback

from app.core.security import get_current_user_id
from app.services.investigation_board_service import (
    ensure_board_write_access,
    get_board_service,
    save_board_service,
)
from app.services.upload_service import upload_board_image_service
from app.schemas.investigation_board_schema import SaveBoardRequest

router = APIRouter(prefix="/cases", tags=["Quadro Investigativo"])


@router.get("/{caso_id}/board")
def get_board(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    board = get_board_service(current_user_id, caso_id)

    if board is None:
        raise HTTPException(status_code=404, detail="Caso não encontrado.")

    return board


@router.put("/{caso_id}/board")
def save_board(
    caso_id: str,
    data: SaveBoardRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        return save_board_service(
            current_user_id,
            caso_id,
            [node.model_dump() for node in data.nodes],
            [edge.model_dump() for edge in data.edges],
        )

    except HTTPException:
        raise

    except Exception as e:
        if "não encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/{caso_id}/board/images", status_code=201)
async def upload_board_image_route(
    caso_id: str,
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id),
):
    if not ensure_board_write_access(current_user_id, caso_id):
        raise HTTPException(status_code=404, detail="Caso não encontrado.")

    file_bytes = await file.read()

    try:
        url = await upload_board_image_service(
            caso_id,
            file_bytes,
            file.content_type
        )
        return {"url": url}

    except Exception as e:
        traceback.print_exc()
        print("ERRO REAL:", repr(e))

        raise

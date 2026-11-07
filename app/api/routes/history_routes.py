from fastapi import APIRouter, Depends

from app.core.security import get_current_user_id
from app.services.history_service import get_case_history_service


router = APIRouter(
    prefix="/history",
    tags=["History"]
)


@router.get("/cases/{caso_id}")
def get_case_history_route(
    caso_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    return get_case_history_service(
        current_user_id,
        caso_id
    )

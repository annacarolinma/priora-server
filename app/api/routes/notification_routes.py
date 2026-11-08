from fastapi import APIRouter, Depends

from app.core.security import get_current_user_id
from app.services.notification_service import (
    list_notifications_service,
    mark_read_service,
    mark_all_read_service,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(current_user_id: str = Depends(get_current_user_id)):
    return list_notifications_service(current_user_id)


@router.post("/read-all")
def read_all(current_user_id: str = Depends(get_current_user_id)):
    return mark_all_read_service(current_user_id)


@router.post("/{notification_id}/read")
def read_one(notification_id: str, current_user_id: str = Depends(get_current_user_id)):
    return mark_read_service(current_user_id, notification_id)

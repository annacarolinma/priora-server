from fastapi import APIRouter, Depends

from app.core.security import get_current_user_id
from app.schemas.priority_schema import UpdateActionStatusRequest
from app.services.priority_service import (
    list_priority_actions_service,
    update_priority_action_status_service,
    delete_priority_action_service,
    list_action_types_service,
)

router = APIRouter(prefix="/priority-actions", tags=["PriorityActions"])


@router.get("/types")
def list_action_types(current_user_id: str = Depends(get_current_user_id)):
    return list_action_types_service()


@router.get("/case/{caso_id}")
def list_priority_actions(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    return list_priority_actions_service(current_user_id, caso_id)


@router.patch("/{action_id}/status")
def update_priority_action_status(
    action_id: str,
    data: UpdateActionStatusRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    return update_priority_action_status_service(current_user_id, action_id, data.status.value)


@router.delete("/{action_id}")
def delete_priority_action(action_id: str, current_user_id: str = Depends(get_current_user_id)):
    return delete_priority_action_service(current_user_id, action_id)

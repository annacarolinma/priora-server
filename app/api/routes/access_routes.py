from fastapi import APIRouter, Depends
from app.core.security import get_current_user_id
from app.services.access_service import (
    invite_user_service,
    accept_invite_service,
    decline_invite_service,
    list_case_users_service,
    update_case_access_service,
    delete_case_access_service
)

from app.schemas.access_schema import (
    InviteUserRequest,
    AcceptInviteRequest,
    UpdateAccessRequest
)

router = APIRouter(prefix="/access", tags=["Access"])


@router.post("/invite", status_code=201)
def invite_user(data: InviteUserRequest, current_user_id: str = Depends(get_current_user_id)):
    return invite_user_service(
        current_user_id,
        data.email,
        data.casoId,
        data.papel
    )


@router.post("/accept")
def accept_invite(data: AcceptInviteRequest, current_user_id: str = Depends(get_current_user_id)):
    return accept_invite_service(
        current_user_id,
        data.userId,
        data.casoId
    )


@router.post("/decline")
def decline_invite(data: AcceptInviteRequest, current_user_id: str = Depends(get_current_user_id)):
    return decline_invite_service(
        current_user_id,
        data.userId,
        data.casoId
    )


@router.get("/case/{caso_id}")
def list_users(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    return list_case_users_service(current_user_id, caso_id)


@router.patch("/case/{caso_id}/user/{user_id}")
def update_access(caso_id: str, user_id: str, data: UpdateAccessRequest, current_user_id: str = Depends(get_current_user_id)):
    return update_case_access_service(
        current_user_id,
        caso_id,
        user_id,
        data.papel
    )


@router.delete("/case/{caso_id}/user/{user_id}")
def delete_access(caso_id: str, user_id: str, current_user_id: str = Depends(get_current_user_id)):
    return delete_case_access_service(current_user_id, caso_id, user_id)
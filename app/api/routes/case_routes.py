from fastapi import APIRouter, Depends
from app.core.security import get_current_user_id
from app.services.case_service import (
    create_case_service,
    get_cases_service,
    get_uncertainty_evolution_service,
    update_uncertainty_service,
    get_case_service,
    update_case_service,
    delete_case_service,
    get_estimated_profile_service,
    update_estimated_profile_service,
)

from app.schemas.case_schema import (
    CreateCaseRequest,
    UpdateUncertaintyRequest,
    UpdateCaseRequest,
    EstimatedProfileRequest,
)

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("/", status_code=201)
def create_case(data: CreateCaseRequest, current_user_id: str = Depends(get_current_user_id)):
    return create_case_service(
        current_user_id,
        data.dict()
    )


@router.get("/user/{user_id}")
def get_cases(user_id: str, current_user_id: str = Depends(get_current_user_id)):
    return get_cases_service(current_user_id, user_id)


@router.get("/user/{user_id}/uncertainty-evolution")
def get_uncertainty_evolution(user_id: str, current_user_id: str = Depends(get_current_user_id)):
    return get_uncertainty_evolution_service(current_user_id, user_id)


@router.get("/{caso_id}")
def get_case(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    return get_case_service(current_user_id, caso_id)


@router.patch("/{caso_id}/uncertainty")
def update_uncertainty(caso_id: str, data: UpdateUncertaintyRequest, current_user_id: str = Depends(get_current_user_id)):
    return update_uncertainty_service(
        current_user_id,
        caso_id,
        data.incerteza
    )


@router.get("/{caso_id}/estimated-profile")
def get_estimated_profile_route(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    return get_estimated_profile_service(current_user_id, caso_id)


@router.put("/{caso_id}/estimated-profile")
def update_estimated_profile_route(caso_id: str, data: EstimatedProfileRequest, current_user_id: str = Depends(get_current_user_id)):
    return update_estimated_profile_service(
        current_user_id,
        caso_id,
        data.dict()
    )


@router.patch("/{caso_id}")
def update_case_route(caso_id: str, data: UpdateCaseRequest, current_user_id: str = Depends(get_current_user_id)):
    return update_case_service(
        current_user_id,
        caso_id,
        data.dict()
    )


@router.delete("/{caso_id}")
def delete_case_route(caso_id: str, current_user_id: str = Depends(get_current_user_id)):
    return delete_case_service(current_user_id, caso_id)


from fastapi import HTTPException, status

from app.database.neo4j import get_session
from app.core.authorization import require_case_role, READ_ROLES, WRITE_ROLES, OWNER_ROLES
from app.services.uncertainty_evolution import aggregate_uncertainty_evolution
from app.repositories.case_repository import (
    get_uncertainty_snapshots_by_user,
    create_case,
    get_cases_by_user,
    update_case_uncertainty,
    get_case_by_id_tx,
    update_case,
    delete_case,
    get_estimated_profile,
    set_estimated_profile,
)

def create_case_service(current_user_id: str, data):
    # o responsável pelo caso é sempre o usuário autenticado, nunca um
    # userId arbitrário enviado no corpo da requisição.
    with get_session() as tx:
        return create_case(tx, current_user_id, data)


def get_cases_service(current_user_id: str, user_id: str):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode consultar seus próprios casos",
        )
    with get_session() as tx:
        return get_cases_by_user(tx, user_id)


def get_uncertainty_evolution_service(current_user_id: str, user_id: str):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode consultar seus próprios casos",
        )
    with get_session() as tx:
        rows = get_uncertainty_snapshots_by_user(tx, user_id)
    return aggregate_uncertainty_evolution(rows)


def get_case_service(current_user_id: str, caso_id: str):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, READ_ROLES)
        return get_case_by_id_tx(tx, caso_id)


def update_uncertainty_service(current_user_id: str, caso_id, nova_incerteza):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        return update_case_uncertainty(tx, caso_id, nova_incerteza)


def update_case_service(current_user_id: str, caso_id, data):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        return update_case(tx, caso_id, data, current_user_id)


def delete_case_service(current_user_id: str, caso_id):
    with get_session() as tx:
        # só o responsável pelo caso pode excluí-lo (doc, seção 10, UC03)
        require_case_role(tx, current_user_id, caso_id, OWNER_ROLES)
        return delete_case(tx, caso_id)


def get_estimated_profile_service(current_user_id: str, caso_id: str):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, READ_ROLES)
        return get_estimated_profile(tx, caso_id)


def update_estimated_profile_service(current_user_id: str, caso_id: str, data):
    # perfil estimado é só visualização (perfilamento criminal): não entra no
    # motor bayesiano, então não dispara recálculo.
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        return set_estimated_profile(tx, caso_id, current_user_id, data)



from fastapi import HTTPException, status as http_status

from app.database.neo4j import get_session
from app.core.authorization import require_case_role, READ_ROLES, WRITE_ROLES
from app.repositories.history_repository import create_history
from app.repositories.priority_repository import (
    upsert_and_list_actions,
    update_action_status,
    get_case_id_for_action,
    get_action_for_exclusion,
    exclude_action,
    action_type_catalog,
)


def list_priority_actions_service(current_user_id: str, caso_id: str):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, READ_ROLES)
        return upsert_and_list_actions(tx, caso_id)


def update_priority_action_status_service(current_user_id: str, action_id: str, new_status: str):
    with get_session() as tx:
        caso_id = get_case_id_for_action(tx, action_id)
        if not caso_id:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        acao = update_action_status(tx, action_id, new_status)
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=caso_id,
            action="UPDATE",
            entity_type="ACAO",
            entity_id=action_id,
            entity_name=acao.get("titulo"),
            details=f"Status: {acao.get('status')}",
        )
        return acao


def delete_priority_action_service(current_user_id: str, action_id: str):
    with get_session() as tx:
        acao = get_action_for_exclusion(tx, action_id)
        if not acao:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
        require_case_role(tx, current_user_id, acao["casoId"], WRITE_ROLES)
        # só ações já descartadas podem ser excluídas (primeiro descarta, depois exclui)
        if acao["status"] != "Descartada":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Só é possível excluir ações descartadas",
            )
        exclude_action(tx, action_id)
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=acao["casoId"],
            action="DELETE",
            entity_type="ACAO",
            entity_id=action_id,
            entity_name=acao.get("titulo"),
            details="Ação excluída",
        )
        return {"deleted": True, "id": action_id}


def list_action_types_service():
    return action_type_catalog()

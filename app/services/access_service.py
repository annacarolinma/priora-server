from fastapi import HTTPException, status

from app.database.neo4j import get_session
from app.core.authorization import require_case_role, READ_ROLES, WRITE_ROLES, OWNER_ROLES
from app.repositories.access_repository import (
    invite_user_to_case,
    accept_invite,
    list_case_users,
    update_case_access,
    delete_case_access,
    get_user_label,
)
from app.repositories.history_repository import create_history


def invite_user_service(current_user_id: str, email, caso_id, papel):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        # quem convida é sempre o usuário autenticado, nunca um userId
        # arbitrário enviado no corpo da requisição.
        convite = invite_user_to_case(tx, email, caso_id, papel, current_user_id)
        usuario = convite.get("usuario") or {}
        nome = f"{usuario.get('primeiroNome', '')} {usuario.get('sobrenome', '')}".strip() or email
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=caso_id,
            action="CREATE",
            entity_type="ACESSO",
            entity_id=usuario.get("id"),
            entity_name=nome,
            details=f"Convidado como {convite.get('papel')}",
        )
        return convite


def accept_invite_service(current_user_id: str, user_id, caso_id):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode aceitar convites destinados à sua própria conta",
        )
    with get_session() as tx:
        resultado = accept_invite(tx, user_id, caso_id)
        create_history(
            tx,
            user_id=user_id,
            caso_id=caso_id,
            action="UPDATE",
            entity_type="ACESSO",
            entity_id=user_id,
            entity_name=get_user_label(tx, user_id),
            details="Convite aceito",
        )
        return resultado


def list_case_users_service(current_user_id: str, caso_id):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, READ_ROLES)
        return list_case_users(tx, caso_id)


def update_case_access_service(current_user_id: str, caso_id, user_id, papel):
    with get_session() as tx:
        # somente o responsável pelo caso pode alterar papéis de colaboradores
        require_case_role(tx, current_user_id, caso_id, OWNER_ROLES)
        acesso = update_case_access(tx, caso_id, user_id, papel)
        usuario = acesso.get("usuario") or {}
        nome = f"{usuario.get('primeiroNome', '')} {usuario.get('sobrenome', '')}".strip() or None
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=caso_id,
            action="UPDATE",
            entity_type="ACESSO",
            entity_id=user_id,
            entity_name=nome,
            details=f"Papel alterado para {acesso.get('papel')}",
        )
        return acesso


def delete_case_access_service(current_user_id: str, caso_id, user_id):
    with get_session() as tx:
        # somente o responsável pelo caso pode remover o acesso de colaboradores
        require_case_role(tx, current_user_id, caso_id, OWNER_ROLES)
        nome = get_user_label(tx, user_id)
        resultado = delete_case_access(tx, caso_id, user_id)
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=caso_id,
            action="DELETE",
            entity_type="ACESSO",
            entity_id=user_id,
            entity_name=nome,
            details="Acesso removido",
        )
        return resultado
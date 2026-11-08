from fastapi import HTTPException, status

from app.database.neo4j import get_session
from app.core.authorization import require_case_role, READ_ROLES, OWNER_ROLES
from app.repositories.access_repository import (
    invite_user_to_case,
    accept_invite,
    list_case_users,
    update_case_access,
    delete_case_access,
    get_user_label,
    decline_invite,
)
from app.services.notification_service import (
    notify_invite,
    notify_invite_answer,
    notify_role_changed,
    notify_access_removed,
)
from app.repositories.notification_repository import mark_invite_read
from app.repositories.history_repository import create_history


def invite_user_service(current_user_id: str, email, caso_id, papel):
    try:
        return _invite_user(current_user_id, email, caso_id, papel)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def _invite_user(current_user_id: str, email, caso_id, papel):
    with get_session() as tx:
        # somente o Responsável pelo caso convida colaboradores
        require_case_role(tx, current_user_id, caso_id, OWNER_ROLES)
        # quem convida é sempre o usuário autenticado, nunca um userId
        # arbitrário enviado no corpo da requisição.
        convite = invite_user_to_case(tx, email, caso_id, papel, current_user_id)
        usuario = convite.get("usuario") or {}
        nome = f"{usuario.get('primeiroNome', '')} {usuario.get('sobrenome', '')}".strip() or email
        if usuario.get("id"):
            notify_invite(tx, current_user_id, usuario["id"], caso_id, convite.get("papel"))
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
    try:
        return _accept_invite(current_user_id, user_id, caso_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def _accept_invite(current_user_id: str, user_id, caso_id):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode aceitar convites destinados à sua própria conta",
        )
    with get_session() as tx:
        resultado = accept_invite(tx, user_id, caso_id)
        mark_invite_read(tx, user_id, caso_id)
        notify_invite_answer(tx, user_id, caso_id, resultado.get("convidadoPor"), True, resultado.get("papel"))
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
        return {"casoId": resultado["casoId"], "status": resultado["status"]}


def decline_invite_service(current_user_id: str, user_id, caso_id):
    try:
        return _decline_invite(current_user_id, user_id, caso_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def _decline_invite(current_user_id: str, user_id, caso_id):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode recusar convites destinados à sua própria conta",
        )
    with get_session() as tx:
        nome = get_user_label(tx, user_id)
        inviter = decline_invite(tx, user_id, caso_id)
        mark_invite_read(tx, user_id, caso_id)
        notify_invite_answer(tx, user_id, caso_id, inviter, False)
        create_history(
            tx,
            user_id=user_id,
            caso_id=caso_id,
            action="DELETE",
            entity_type="ACESSO",
            entity_id=user_id,
            entity_name=nome,
            details="Convite recusado",
        )
        return {"casoId": caso_id, "status": "Recusado"}


def list_case_users_service(current_user_id: str, caso_id):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, READ_ROLES)
        return list_case_users(tx, caso_id)


def update_case_access_service(current_user_id: str, caso_id, user_id, papel):
    with get_session() as tx:
        # somente o responsável pelo caso pode alterar papéis de colaboradores
        require_case_role(tx, current_user_id, caso_id, OWNER_ROLES)
        acesso = update_case_access(tx, caso_id, user_id, papel)
        notify_role_changed(tx, current_user_id, user_id, caso_id, acesso.get("papel"))
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
        notify_access_removed(tx, current_user_id, user_id, caso_id)
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
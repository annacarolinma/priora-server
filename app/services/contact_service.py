from fastapi import HTTPException, status

from app.database.neo4j import get_session
from app.core.authorization import require_case_role, READ_ROLES, WRITE_ROLES
from app.repositories.contact_repository import (
    create_contact,
    list_contacts_by_case,
    update_contact,
    delete_contact,
    get_case_id_for_contact,
    get_contact_name,
)
from app.repositories.history_repository import create_history


def create_contact_service(current_user_id: str, data):
    with get_session() as tx:
        require_case_role(tx, current_user_id, data["casoId"], WRITE_ROLES)
        contato = create_contact(tx, data)
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=data["casoId"],
            action="CREATE",
            entity_type="CONTATO",
            entity_id=contato.get("id"),
            entity_name=contato.get("nome"),
            details=f"Cargo: {contato.get('cargo')}" if contato.get("cargo") else None,
        )
        return contato


def list_contacts_service(current_user_id: str, caso_id):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, READ_ROLES)
        return list_contacts_by_case(tx, caso_id)


def update_contact_service(current_user_id: str, contato_id, data):
    with get_session() as tx:
        caso_id = get_case_id_for_contact(tx, contato_id)
        if not caso_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contato não encontrado")
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        contato = update_contact(tx, contato_id, data)
        campos = [c for c in ("nome", "cargo", "celular") if data.get(c) is not None]
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=caso_id,
            action="UPDATE",
            entity_type="CONTATO",
            entity_id=contato_id,
            entity_name=contato.get("nome"),
            details=f"campos: {', '.join(campos)}" if campos else None,
        )
        return contato


def delete_contact_service(current_user_id: str, caso_id, contato_id):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        nome = get_contact_name(tx, contato_id)
        resultado = delete_contact(tx, caso_id, contato_id)
        create_history(
            tx,
            user_id=current_user_id,
            caso_id=caso_id,
            action="DELETE",
            entity_type="CONTATO",
            entity_id=contato_id,
            entity_name=nome,
        )
        return resultado
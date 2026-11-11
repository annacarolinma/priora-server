from app.services.notification_service import notify_suspect_added
from fastapi import HTTPException, status

from app.database.neo4j import get_session

from app.core.authorization import (
    require_case_role,
    READ_ROLES,
    WRITE_ROLES
)

from app.services.bayes_service import recalculate_case

from app.repositories.history_repository import create_history

from app.repositories.suspect_repository import (
    create_suspect,
    list_suspects_by_case,
    update_suspect_ranking,
    update_suspect,
    delete_suspect,
    get_case_id_for_suspect,
    get_suspect_by_id,
)


def compare_suspect_changes(before, after):

    fields = [
        "nome",
        "idade",
        "fotoUrl",
        "descricao",
        "historicoCriminal",
        "caracteristicasCriminais",
        "significanciaTempoLugar",
        "coerenciaInterpessoal",
        "conscienciaForense",
        "crimeSimilarAntes",
        "histDescumprimento",
    ]

    changes = []

    for field in fields:

        old = before.get(field)
        new = after.get(field)

        if old != new:
            changes.append({
                "campo": field,
                "antes": old,
                "depois": new
            })

    return changes



def create_suspect_service(
    current_user_id: str,
    data
):

    with get_session() as tx:

        require_case_role(
            tx,
            current_user_id,
            data["casoId"],
            WRITE_ROLES
        )

        suspect = create_suspect(
            tx,
            data
        )


        create_history(
            tx,
            user_id=current_user_id,
            caso_id=data["casoId"],
            action="CREATE",
            entity_type="SUSPEITO",
            entity_id=suspect["id"],
            entity_name=suspect["nome"],
            valor_novo=suspect
        )


        recalculate_case(
            tx,
            data["casoId"]
        )

        notify_suspect_added(tx, current_user_id, data["casoId"], suspect.get("nome") or "sem nome")


        return suspect



def list_suspects_service(
    current_user_id: str,
    caso_id
):

    with get_session() as tx:

        require_case_role(
            tx,
            current_user_id,
            caso_id,
            READ_ROLES
        )

        return list_suspects_by_case(
            tx,
            caso_id
        )



def update_suspect_ranking_service(
    current_user_id: str,
    caso_id
):

    with get_session() as tx:

        require_case_role(
            tx,
            current_user_id,
            caso_id,
            WRITE_ROLES
        )

        return update_suspect_ranking(
            tx,
            caso_id
        )



def update_suspect_service(
    current_user_id: str,
    suspect_id,
    data
):

    with get_session() as tx:


        caso_id = get_case_id_for_suspect(
            tx,
            suspect_id
        )


        if not caso_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suspeito não encontrado"
            )


        require_case_role(
            tx,
            current_user_id,
            caso_id,
            WRITE_ROLES
        )


        old_suspect = get_suspect_by_id(
            tx,
            suspect_id
        )


        new_suspect = update_suspect(
            tx,
            suspect_id,
            data
        )


        changes = compare_suspect_changes(
            old_suspect,
            new_suspect
        )


        if changes:

            create_history(
                tx,
                user_id=current_user_id,
                caso_id=caso_id,
                action="UPDATE",
                entity_type="SUSPEITO",
                entity_id=suspect_id,
                entity_name=new_suspect["nome"],
                details=changes
            )


        recalculate_case(
            tx,
            caso_id
        )


        return new_suspect



def delete_suspect_service(
    current_user_id: str,
    caso_id,
    suspect_id
):

    with get_session() as tx:


        require_case_role(
            tx,
            current_user_id,
            caso_id,
            WRITE_ROLES
        )


        suspect = get_suspect_by_id(
            tx,
            suspect_id
        )


        if not suspect:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suspeito não encontrado"
            )



        result = delete_suspect(
            tx,
            caso_id,
            suspect_id
        )



        create_history(
            tx,
            user_id=current_user_id,
            caso_id=caso_id,
            action="DELETE",
            entity_type="SUSPEITO",
            entity_id=suspect_id,
            entity_name=suspect["nome"]
        )



        recalculate_case(
            tx,
            caso_id
        )


        return result
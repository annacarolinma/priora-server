from fastapi import HTTPException, status

from app.database.neo4j import get_session
from app.repositories import notification_repository as repo
from app.repositories.access_repository import get_user_label

# Tipos de notificação
CONVITE = "CONVITE"
CONVITE_ACEITO = "CONVITE_ACEITO"
CONVITE_RECUSADO = "CONVITE_RECUSADO"
PAPEL_ALTERADO = "PAPEL_ALTERADO"
ACESSO_REMOVIDO = "ACESSO_REMOVIDO"
EVIDENCIA_NOVA = "EVIDENCIA_NOVA"
SUSPEITO_NOVO = "SUSPEITO_NOVO"


def _nome(tx, user_id):
    return get_user_label(tx, user_id) or "Um colaborador"


def notify_users(tx, recipient_ids, tipo, mensagem, caso_id, ator_id):
    return repo.create_notifications(tx, recipient_ids, tipo, mensagem, caso_id, ator_id)


def notify_case_members(tx, caso_id, ator_id, tipo, mensagem):
    """Avisa responsável e colaboradores ativos do caso, menos quem fez a ação."""
    return repo.create_notifications(
        tx, repo.get_case_member_ids(tx, caso_id), tipo, mensagem, caso_id, ator_id
    )


# ---- gatilhos usados pelos outros serviços -----------------------------

def notify_invite(tx, ator_id, invitee_id, caso_id, papel):
    caso = repo.get_case_name(tx, caso_id) or "um caso"
    notify_users(
        tx, [invitee_id], CONVITE,
        f"{_nome(tx, ator_id)} convidou você para o caso {caso} como {papel}.",
        caso_id, ator_id,
    )


def notify_invite_answer(tx, user_id, caso_id, inviter_id, accepted, papel=None):
    caso = repo.get_case_name(tx, caso_id) or "o caso"
    owner = repo.get_case_owner_id(tx, caso_id)
    nome = _nome(tx, user_id)
    if accepted:
        tipo = CONVITE_ACEITO
        msg = f"{nome} aceitou o convite e agora tem acesso de {papel} ao caso {caso}."
    else:
        tipo = CONVITE_RECUSADO
        msg = f"{nome} recusou o convite para o caso {caso}."
    notify_users(tx, [inviter_id, owner], tipo, msg, caso_id, user_id)


def notify_role_changed(tx, ator_id, user_id, caso_id, papel):
    caso = repo.get_case_name(tx, caso_id) or "o caso"
    notify_users(
        tx, [user_id], PAPEL_ALTERADO,
        f"{_nome(tx, ator_id)} alterou seu papel no caso {caso} para {papel}.",
        caso_id, ator_id,
    )


def notify_access_removed(tx, ator_id, user_id, caso_id):
    caso = repo.get_case_name(tx, caso_id) or "o caso"
    notify_users(
        tx, [user_id], ACESSO_REMOVIDO,
        f"{_nome(tx, ator_id)} removeu seu acesso ao caso {caso}.",
        caso_id, ator_id,
    )


def notify_evidence_added(tx, ator_id, caso_id, nome_evidencia):
    caso = repo.get_case_name(tx, caso_id) or "o caso"
    notify_case_members(
        tx, caso_id, ator_id, EVIDENCIA_NOVA,
        f"{_nome(tx, ator_id)} adicionou a evidência \"{nome_evidencia}\" ao caso {caso}.",
    )


def notify_suspect_added(tx, ator_id, caso_id, nome_suspeito):
    caso = repo.get_case_name(tx, caso_id) or "o caso"
    notify_case_members(
        tx, caso_id, ator_id, SUSPEITO_NOVO,
        f"{_nome(tx, ator_id)} adicionou o suspeito \"{nome_suspeito}\" ao caso {caso}.",
    )


# ---- serviços das rotas ------------------------------------------------

def list_notifications_service(user_id: str):
    with get_session() as tx:
        return repo.list_notifications(tx, user_id)


def mark_read_service(user_id: str, notification_id: str):
    with get_session() as tx:
        if not repo.mark_read(tx, user_id, notification_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificação não encontrada")
        return {"ok": True}


def mark_all_read_service(user_id: str):
    with get_session() as tx:
        repo.mark_all_read(tx, user_id)
        return {"ok": True}

import json

from app.database.neo4j import get_session
from app.core.authorization import require_case_role, READ_ROLES, WRITE_ROLES
from app.repositories.investigation_board_repository import (
    get_case_exists,
    get_board,
    save_board,
)


def ensure_board_write_access(current_user_id: str, caso_id: str):
    """Exige papel Editor/Responsável no caso (usado também no upload de imagens)."""
    with get_session() as tx:
        if not get_case_exists(tx, caso_id):
            return False
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
    return True


def get_board_service(current_user_id: str, caso_id: str):
    """
    Retorna:
      - None                         -> caso não existe (rota deve responder 404)
      - {"nodes": [], "edges": []}   -> caso existe, mas quadro ainda não foi salvo
      - {"nodes": [...], "edges": [...]} -> quadro salvo
    """
    with get_session() as tx:
        if not get_case_exists(tx, caso_id):
            return None

        require_case_role(tx, current_user_id, caso_id, READ_ROLES)

        raw = get_board(tx, caso_id)

    if not raw:
        return {"nodes": [], "edges": []}

    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        # dado corrompido/manual no banco — não derruba a rota, volta vazio
        return {"nodes": [], "edges": []}


def save_board_service(current_user_id: str, caso_id: str, nodes: list, edges: list):
    with get_session() as tx:
        require_case_role(tx, current_user_id, caso_id, WRITE_ROLES)
        return save_board(tx, caso_id, nodes, edges)

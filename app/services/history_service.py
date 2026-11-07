from app.database.neo4j import get_session
from app.core.authorization import require_case_role, READ_ROLES
from app.repositories.history_repository import get_case_history


def get_case_history_service(user_id: str, caso_id: str):
    """
    Retorna o histórico de TODOS os colaboradores do caso (não apenas do
    usuário logado), desde que o usuário tenha ao menos acesso de leitura.
    """
    with get_session() as tx:
        require_case_role(tx, user_id, caso_id, READ_ROLES)
        return get_case_history(tx, caso_id)

"""
Notificações do usuário.

Modelo no Neo4j: (:Usuario)-[:RECEBEU]->(:Notificacao {id, tipo, mensagem, casoId,
atorId, lida, criadaEm}). Cada destinatário recebe a sua própria cópia, então
"lida" é individual.
"""

LIST_LIMIT = 30


def create_notifications(tx, recipient_ids, tipo, mensagem, caso_id, ator_id):
    ids = [uid for uid in dict.fromkeys(recipient_ids) if uid and uid != ator_id]
    if not ids:
        return 0
    result = tx.run(
        """
        UNWIND $ids AS uid
        MATCH (u:Usuario {id: uid})
        CREATE (u)-[:RECEBEU]->(n:Notificacao {
            id: randomUUID(),
            tipo: $tipo,
            mensagem: $mensagem,
            casoId: $casoId,
            atorId: $atorId,
            lida: false,
            criadaEm: datetime()
        })
        RETURN count(n) AS n
        """,
        ids=ids, tipo=tipo, mensagem=mensagem, casoId=caso_id, atorId=ator_id,
    ).single()
    return result["n"] if result else 0


def get_case_member_ids(tx, caso_id):
    """Responsável e colaboradores com acesso ativo ao caso."""
    rows = tx.run(
        """
        MATCH (c:Caso {id: $casoId})
        OPTIONAL MATCH (r:Usuario)-[:RESPONSAVEL_POR]->(c)
        OPTIONAL MATCH (u:Usuario)-[a:TEM_ACESSO]->(c) WHERE a.status = 'Ativo'
        WITH collect(DISTINCT r.id) + collect(DISTINCT u.id) AS ids
        UNWIND ids AS id
        WITH id WHERE id IS NOT NULL
        RETURN DISTINCT id
        """,
        casoId=caso_id,
    ).data()
    return [row["id"] for row in rows]


def get_case_owner_id(tx, caso_id):
    row = tx.run(
        "MATCH (r:Usuario)-[:RESPONSAVEL_POR]->(:Caso {id: $casoId}) RETURN r.id AS id",
        casoId=caso_id,
    ).single()
    return row["id"] if row else None


def get_case_name(tx, caso_id):
    row = tx.run("MATCH (c:Caso {id: $id}) RETURN c.nome AS nome", id=caso_id).single()
    return row["nome"] if row else None


def list_notifications(tx, user_id):
    rows = tx.run(
        """
        MATCH (:Usuario {id: $userId})-[:RECEBEU]->(n:Notificacao)
        OPTIONAL MATCH (:Usuario {id: $userId})-[a:TEM_ACESSO]->(c:Caso {id: n.casoId})
        RETURN n.id AS id, n.tipo AS tipo, n.mensagem AS mensagem, n.casoId AS casoId,
               n.lida AS lida, toString(n.criadaEm) AS criadaEm,
               CASE WHEN n.tipo = 'CONVITE' THEN a.status ELSE null END AS conviteStatus
        ORDER BY n.criadaEm DESC
        LIMIT $limit
        """,
        userId=user_id, limit=LIST_LIMIT,
    ).data()
    unread = tx.run(
        "MATCH (:Usuario {id: $userId})-[:RECEBEU]->(n:Notificacao {lida: false}) RETURN count(n) AS n",
        userId=user_id,
    ).single()["n"]
    return {"items": rows, "naoLidas": unread}


def mark_read(tx, user_id, notification_id):
    row = tx.run(
        """
        MATCH (:Usuario {id: $userId})-[:RECEBEU]->(n:Notificacao {id: $id})
        SET n.lida = true
        RETURN n.id AS id
        """,
        userId=user_id, id=notification_id,
    ).single()
    return row is not None


def mark_all_read(tx, user_id):
    tx.run(
        "MATCH (:Usuario {id: $userId})-[:RECEBEU]->(n:Notificacao {lida: false}) SET n.lida = true",
        userId=user_id,
    )


def mark_invite_read(tx, user_id, caso_id):
    """Convite respondido: a notificação deixa de ser pendente."""
    tx.run(
        """
        MATCH (:Usuario {id: $userId})-[:RECEBEU]->(n:Notificacao {tipo: 'CONVITE', casoId: $casoId})
        SET n.lida = true
        """,
        userId=user_id, casoId=caso_id,
    )

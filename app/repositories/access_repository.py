def get_user_role_for_case(tx, user_id, caso_id):
    """
    Retorna o papel do usuário no caso: 'Responsavel', 'Editor', 'Leitor'
    ou None se o usuário não tiver nenhum acesso (ou o convite ainda
    estiver 'Pendente').
    """
    query = """
    MATCH (c:Caso {id: $casoId}), (u:Usuario {id: $userId})
    OPTIONAL MATCH (u)-[resp:RESPONSAVEL_POR]->(c)
    OPTIONAL MATCH (u)-[acesso:TEM_ACESSO]->(c)
    RETURN resp IS NOT NULL AS isResponsavel,
           acesso.papel AS papel,
           acesso.status AS status
    """
    record = tx.run(query, userId=user_id, casoId=caso_id).single()

    if not record:
        return None

    if record["isResponsavel"]:
        return "Responsavel"

    if record["papel"] and record["status"] == "Ativo":
        return record["papel"]

    return None


def invite_user_to_case(tx, email, caso_id, papel, user_id):
    query = """
    MATCH (sender:Usuario {id: $userId})
    MATCH (u:Usuario {email: $email})
    MATCH (c:Caso {id: $casoId})

    OPTIONAL MATCH (sender)-[:RESPONSAVEL_POR]->(c)
    OPTIONAL MATCH (sender)-[senderAccess:TEM_ACESSO]->(c)

    WITH sender, u, c, senderAccess
    WHERE sender.id <> u.id

    MERGE (u)-[r:TEM_ACESSO]->(c)
    ON CREATE SET
        r.papel = $papel,
        r.status = 'Pendente',
        r.convidadoPor = $userId,
        r.convidadoEm = datetime()
    ON MATCH SET
        r.papel = $papel

    RETURN u {
        .id, .email, .primeiroNome, .sobrenome
    } AS usuario,
    r.papel AS papel,
    r.status AS status
    """

    result = tx.run(
        query,
        email=email,
        casoId=caso_id,
        papel=papel,
        userId=user_id
    )

    record = result.single()

    if not record:
        raise Exception("Usuário não encontrado ou convite inválido")

    return record.data()


def accept_invite(tx, user_id, caso_id):
    query = """
    MATCH (u:Usuario {id: $userId})-[r:TEM_ACESSO]->(c:Caso {id: $casoId})
    SET r.status = 'Ativo'
    RETURN c.id AS casoId, r.status AS status, r.papel AS papel, r.convidadoPor AS convidadoPor
    """
    result = tx.run(query,
        userId=user_id,
        casoId=caso_id
    )
    record = result.single()
    if not record:
        raise Exception("Convite não encontrado")
    return record.data()


def list_case_users(tx, caso_id):
    query = """
    MATCH (c:Caso {id: $casoId})

    OPTIONAL MATCH (owner:Usuario)-[:RESPONSAVEL_POR]->(c)
    OPTIONAL MATCH (u:Usuario)-[r:TEM_ACESSO]->(c)

    WITH
      collect(DISTINCT {
        usuario: owner {
          .id, .email, .primeiroNome, .sobrenome
        },
        papel: 'Editor',
        status: 'Ativo',
        tipo: 'Responsavel'
      }) +
      collect(DISTINCT {
        usuario: u {
          .id, .email, .primeiroNome, .sobrenome
        },
        papel: r.papel,
        status: r.status,
        tipo: 'Colaborador'
      }) AS acessos

    UNWIND acessos AS acesso
    WITH acesso
    WHERE acesso.usuario.id IS NOT NULL

    RETURN acesso.usuario AS usuario,
           acesso.papel AS papel,
           acesso.status AS status,
           acesso.tipo AS tipo
    """
    result = tx.run(query, casoId=caso_id)
    return [record.data() for record in result]


def update_case_access(tx, caso_id, user_id, papel):
    query = """
    MATCH (u:Usuario {id: $userId})-[r:TEM_ACESSO]->(c:Caso {id: $casoId})
    SET r.papel = $papel
    RETURN u {
        .id, .email, .primeiroNome, .sobrenome
    } AS usuario,
    r.papel AS papel,
    r.status AS status
    """
    result = tx.run(
        query,
        casoId=caso_id,
        userId=user_id,
        papel=papel
    )

    record = result.single()

    if not record:
        raise Exception("Acesso não encontrado")

    return record.data()


def delete_case_access(tx, caso_id, user_id):
    query = """
    MATCH (u:Usuario {id: $userId})-[r:TEM_ACESSO]->(c:Caso {id: $casoId})
    DELETE r
    RETURN u.id AS userId, c.id AS casoId
    """
    result = tx.run(
        query,
        casoId=caso_id,
        userId=user_id
    )

    record = result.single()

    if not record:
        raise Exception("Acesso não encontrado")

    return {
        "deleted": True,
        "userId": record["userId"],
        "casoId": record["casoId"]
    }


def get_user_label(tx, user_id: str) -> str | None:
    """Nome completo do usuário (para registrar no histórico)."""
    record = tx.run(
        "MATCH (u:Usuario {id: $id}) RETURN u.primeiroNome + ' ' + u.sobrenome AS nome",
        id=user_id,
    ).single()
    return record["nome"] if record else None


def decline_invite(tx, user_id, caso_id):
    """Recusa: remove o convite pendente. Devolve quem convidou (ou None)."""
    record = tx.run(
        """
        MATCH (u:Usuario {id: $userId})-[r:TEM_ACESSO]->(c:Caso {id: $casoId})
        WHERE r.status = 'Pendente'
        WITH r, r.convidadoPor AS convidadoPor
        DELETE r
        RETURN convidadoPor
        """,
        userId=user_id, casoId=caso_id,
    ).single()
    if not record:
        raise Exception("Convite não encontrado")
    return record["convidadoPor"]

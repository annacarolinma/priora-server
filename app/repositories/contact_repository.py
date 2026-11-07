def get_case_id_for_contact(tx, contato_id: str) -> str | None:
    query = """
    MATCH (c:Caso)-[:TEM_CONTATO]->(ct:Contato {id: $contatoId})
    RETURN c.id AS casoId
    """
    record = tx.run(query, contatoId=contato_id).single()
    return record["casoId"] if record else None


def create_contact(tx, data):
    query = """
    MATCH (c:Caso {id: $casoId})
    CREATE (ct:Contato {
        id: randomUUID(),
        nome: $nome,
        cargo: $cargo,
        celular: $celular,
        criadoEm: datetime(),
        atualizadoEm: datetime()
    })
    CREATE (c)-[:TEM_CONTATO {adicionadoEm: datetime()}]->(ct)
    RETURN ct { .id, .nome, .cargo, .celular } AS contato
    """

    result = tx.run(query, **data)
    record = result.single()

    if not record:
        raise Exception("Caso não encontrado")

    return record["contato"]


def list_contacts_by_case(tx, caso_id):
    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_CONTATO]->(ct:Contato)
    RETURN ct {
        .id,
        .nome,
        .cargo,
        .celular
    } AS contato
    ORDER BY ct.criadoEm ASC
    """

    result = tx.run(query, casoId=caso_id)
    return [record["contato"] for record in result]


def update_contact(tx, contato_id, data):
    query = """
    MATCH (ct:Contato {id: $contatoId})
    SET ct.nome = coalesce($nome, ct.nome),
        ct.cargo = coalesce($cargo, ct.cargo),
        ct.celular = coalesce($celular, ct.celular),
        ct.atualizadoEm = datetime()
    RETURN ct { .id, .nome, .cargo, .celular } AS contato
    """

    result = tx.run(
        query,
        contatoId=contato_id,
        nome=data.get("nome"),
        cargo=data.get("cargo"),
        celular=data.get("celular")
    )

    record = result.single()

    if not record:
        raise Exception("Contato não encontrado")

    return record["contato"]


def delete_contact(tx, caso_id, contato_id):
    query = """
    MATCH (c:Caso {id: $casoId})-[r:TEM_CONTATO]->(ct:Contato {id: $contatoId})
    DELETE r, ct
    RETURN $contatoId AS id
    """

    result = tx.run(query, casoId=caso_id, contatoId=contato_id)
    record = result.single()

    if not record:
        raise Exception("Contato não encontrado nesse caso")

    return {"deleted": True, "id": record["id"]}


def get_contact_name(tx, contato_id: str) -> str | None:
    record = tx.run(
        "MATCH (ct:Contato {id: $id}) RETURN ct.nome AS nome",
        id=contato_id,
    ).single()
    return record["nome"] if record else None

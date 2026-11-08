def create_user(tx, email, primeiro_nome, sobrenome, senha_hash):
    query = """
    CREATE (u:Usuario {
        id: randomUUID(),
        email: $email,
        primeiroNome: $primeiro_nome,
        sobrenome: $sobrenome,
        senhaHash: $senha_hash,
        criadoEm: datetime(),
        ultimoAcesso: datetime()
    })
    RETURN u {
        .id, .email, .primeiroNome, .sobrenome, .criadoEm
    } AS user
    """
    result = tx.run(query,
        email=email,
        primeiro_nome=primeiro_nome,
        sobrenome=sobrenome,
        senha_hash=senha_hash
    )
    return result.single()["user"]


def login_user(tx, email):
    query = """
    MATCH (u:Usuario {email: $email})
    SET u.ultimoAcesso = datetime()
    RETURN u {
        .id,
        .email,
        .primeiroNome,
        .sobrenome,
        .fotoUrl,
        .cargo,
        .senhaHash
    } AS user
    """
    result = tx.run(query, email=email)
    record = result.single()

    return record["user"] if record else None


def set_recovery_token(tx, email, token):
    query = """
    MATCH (u:Usuario {email: $email})
    SET u.tokenRecuperacao = $token,
        u.tokenExpiracaoEm = datetime() + duration({minutes: 30})
    RETURN u.email AS email
    """
    result = tx.run(query, email=email, token=token)
    return result.single()


def reset_password(tx, token, nova_senha_hash):
    query = """
    MATCH (u:Usuario {tokenRecuperacao: $token})
    WHERE u.tokenExpiracaoEm > datetime()
    SET u.senhaHash = $novaSenhaHash,
        u.atualizadoEm = datetime()
    REMOVE u.tokenRecuperacao, u.tokenExpiracaoEm
    RETURN u.id AS id
    """
    result = tx.run(query, token=token, novaSenhaHash=nova_senha_hash)
    return result.single()


def check_email_exists(tx, email):
    query = """
    MATCH (u:Usuario {email: $email})
    RETURN u.email AS email
    """
    result = tx.run(query, email=email)
    return result.single() is not None

def get_user_by_id(tx, user_id):
    query = """
    MATCH (u:Usuario {id: $user_id})

    OPTIONAL MATCH (u)-[:RESPONSAVEL_POR]->(casoResponsavel:Caso)

    OPTIONAL MATCH (u)-[:TEM_ACESSO {status: 'Ativo'}]->(casoAcesso:Caso)

    WITH u,
         collect(DISTINCT casoResponsavel) +
         collect(DISTINCT casoAcesso) AS todosCasos

    WITH u,
         [c IN todosCasos WHERE c IS NOT NULL] AS casos

    RETURN u {
        .id,
        .email,
        .primeiroNome,
        .sobrenome,
        .fotoUrl,
        .cargo
    } AS user,

    size(casos) AS totalCasos,

    size([
        c IN casos
        WHERE c.status = 'Ativo'
    ]) AS casosAtivos,

    size([
        c IN casos
        WHERE c.status <> 'Ativo'
    ]) AS casosConcluidos
    """

    result = tx.run(
        query,
        user_id=user_id
    )

    record = result.single()

    if not record:
        return None

    user = dict(record["user"])

    user["totalCasos"] = record["totalCasos"]
    user["casosAtivos"] = record["casosAtivos"]
    user["casosConcluidos"] = record["casosConcluidos"]

    return user

def update_user(tx, user_id, email, primeiro_nome, sobrenome, cargo=None):
    # cargo: None mantém o atual; texto vazio remove; senão grava sem espaços nas pontas
    query = """
    MATCH (u:Usuario {id: $user_id})
    SET u.email = $email,
        u.primeiroNome = $primeiro_nome,
        u.sobrenome = $sobrenome,
        u.cargo = CASE
            WHEN $cargo IS NULL THEN u.cargo
            WHEN trim($cargo) = '' THEN null
            ELSE trim($cargo)
        END,
        u.atualizadoEm = datetime()

    RETURN u {
        .id,
        .email,
        .primeiroNome,
        .sobrenome,
        .fotoUrl,
        .cargo
    } AS user
    """

    result = tx.run(
        query,
        user_id=user_id,
        email=email,
        primeiro_nome=primeiro_nome,
        sobrenome=sobrenome,
        cargo=cargo
    )

    record = result.single()

    return record["user"] if record else None

def get_user_password(tx, user_id):
    query = """
    MATCH (u:Usuario {id: $user_id})
    RETURN u.senhaHash AS senhaHash
    """

    result = tx.run(query, user_id=user_id)
    record = result.single()

    return record["senhaHash"] if record else None

def update_user_password(tx, user_id, senha_hash):
    query = """
    MATCH (u:Usuario {id: $user_id})
    SET u.senhaHash = $senha_hash,
        u.atualizadoEm = datetime()

    RETURN u.id AS id
    """

    result = tx.run(
        query,
        user_id=user_id,
        senha_hash=senha_hash
    )

    return result.single()

def update_user_photo(tx, user_id, foto_base64):
    query = """
    MATCH (u:Usuario {id: $user_id})

    SET u.fotoUrl = $foto_base64,
        u.atualizadoEm = datetime()

    RETURN u {
        .id,
        .email,
        .primeiroNome,
        .sobrenome,
        .fotoUrl,
        .cargo
    } AS user
    """

    result = tx.run(
        query,
        user_id=user_id,
        foto_base64=foto_base64
    )

    record = result.single()

    return record["user"] if record else None
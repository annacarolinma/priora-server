from app.repositories.history_repository import create_history


# ============================================================
# CRIAR CASO
# ============================================================

def create_case(tx, user_id, data):
    query = """
    MATCH (u:Usuario {id: $userId})

    CREATE (c:Caso {
        id: randomUUID(),
        nome: $nome,
        descricao: $descricao,
        status: $status,
        prioridade: $prioridade,

        enderecoCep: $cep,
        enderecoLogradouro: $logradouro,
        enderecoNumero: $numero,
        enderecoBairro: $bairro,
        enderecoCidade: $cidade,
        enderecoEstado: $estado,

        dataOcorrencia: date($dataOcorrencia),

        incerteza: 100.0,

        criadoEm: datetime(),
        atualizadoEm: datetime()
    })

    CREATE (u)-[:RESPONSAVEL_POR {
        atribuidoEm: datetime()
    }]->(c)

    RETURN c {
        .id,
        .nome,
        .status,
        .prioridade,
        .incerteza
    } AS caso
    """

    result = tx.run(
        query,
        userId=user_id,
        nome=data["nome"],
        descricao=data["descricao"],
        status=data["status"],
        prioridade=data["prioridade"],
        cep=data.get("enderecoCep"),
        logradouro=data.get("enderecoLogradouro"),
        numero=data.get("enderecoNumero"),
        bairro=data.get("enderecoBairro"),
        cidade=data.get("enderecoCidade"),
        estado=data.get("enderecoEstado"),
        dataOcorrencia=data.get("dataOcorrencia"),
    )

    record = result.single()

    if not record:
        raise Exception("Erro ao criar caso")

    caso = record["caso"]

    # HISTÓRICO
    create_history(
        tx=tx,
        user_id=user_id,
        caso_id=caso["id"],
        action="CREATE",
        entity_type="CASO",
        entity_id=caso["id"],
        entity_name=caso["nome"],
        details="Caso criado",
    )

    return caso


# ============================================================
# BUSCAR CASOS DO USUÁRIO
# ============================================================

def get_cases_by_user(tx, user_id):
    query = """
    MATCH (u:Usuario {id: $userId})

    OPTIONAL MATCH (u)-[:RESPONSAVEL_POR]->(c1:Caso)

    OPTIONAL MATCH (u)-[:TEM_ACESSO {status: 'Ativo'}]->(c2:Caso)

    WITH collect(c1) + collect(c2) AS todos

    UNWIND todos AS c

    WITH c
    WHERE c IS NOT NULL

    OPTIONAL MATCH (c)-[:TEM_SUSPEITO]->(s:Suspeito)

    OPTIONAL MATCH (c)-[:TEM_EVIDENCIA]->(e:Evidencia)

    OPTIONAL MATCH (resp:Usuario)-[:RESPONSAVEL_POR]->(c)

    WITH
        c,
        resp,
        collect(DISTINCT s)[0] AS topSuspeito,
        count(DISTINCT s) AS qtdSuspeitos,
        count(DISTINCT e) AS qtdEvidencias,
        c.atualizadoEm AS atualizadoEm

    RETURN DISTINCT
        c.id AS id,
        c.nome AS nome,
        c.descricao AS descricao,
        c.status AS status,
        c.prioridade AS prioridade,
        c.incerteza AS incerteza,
        c.dataOcorrencia AS dataOcorrencia,
        c.enderecoCidade AS cidade,
        c.enderecoEstado AS estado,

        resp.primeiroNome AS responsavelPrimeiroNome,
        resp.sobrenome AS responsavelSobrenome,

        topSuspeito.nome AS topSuspeitoNome,
        topSuspeito.probabilidadeAtual AS topSuspeitoProbab,
        topSuspeito.fotoUrl AS topSuspeitoFotoUrl,

        qtdSuspeitos,
        qtdEvidencias,

        atualizadoEm

    ORDER BY atualizadoEm DESC
    """

    result = tx.run(
        query,
        userId=user_id
    )

    return [
        {
            **record.data(),
            "dataOcorrencia": (
                str(record["dataOcorrencia"])
                if record["dataOcorrencia"]
                else None
            )
        }
        for record in result
    ]


# ============================================================
# ALTERAR INCERTEZA
# ============================================================

def update_case_uncertainty(tx, caso_id, nova_incerteza, user_id=None):
    query = """
    MATCH (c:Caso {id: $casoId})

    SET
        c.incerteza = $novaIncerteza,
        c.atualizadoEm = datetime()

    RETURN
        c.id AS id,
        c.incerteza AS incerteza
    """

    result = tx.run(
        query,
        casoId=caso_id,
        novaIncerteza=nova_incerteza
    )

    record = result.single()

    if not record:
        raise Exception("Caso não encontrado")

    resultado = record.data()

    # HISTÓRICO
    if user_id:
        create_history(
            tx=tx,
            user_id=user_id,
            caso_id=caso_id,
            action="UPDATE",
            entity_type="CASO",
            entity_id=caso_id,
            details=f"Incerteza alterada para {nova_incerteza}",
        )

    return resultado


# ============================================================
# BUSCAR CASO POR ID
# ============================================================

def get_case_by_id_tx(tx, case_id):
    query = """
    MATCH (c:Caso {id: $caseId})

    OPTIONAL MATCH (u:Usuario)-[:RESPONSAVEL_POR]->(c)

    OPTIONAL MATCH (c)-[:TEM_SUSPEITO]->(s:Suspeito)

    WITH
        c,
        u,
        count(DISTINCT s) AS totalSuspeitos

    OPTIONAL MATCH (c)-[:TEM_EVIDENCIA]->(e:Evidencia)

    WITH
        c,
        u,
        totalSuspeitos,
        count(DISTINCT e) AS totalEvidencias

    RETURN c {
        .id,
        .nome,
        .descricao,
        .status,
        .prioridade,

        .enderecoCep,
        .enderecoLogradouro,
        .enderecoNumero,
        .enderecoBairro,
        .enderecoCidade,
        .enderecoEstado,

        .incerteza,

        dataOcorrencia: toString(c.dataOcorrencia),
        criadoEm: toString(c.criadoEm),
        atualizadoEm: toString(c.atualizadoEm),

        totalSuspeitos: totalSuspeitos,
        totalEvidencias: totalEvidencias,

        responsavel: u {
            .id,
            .primeiroNome,
            .sobrenome,
            .email
        }
    } AS caso
    """

    result = tx.run(
        query,
        caseId=case_id
    )

    record = result.single()

    return record["caso"] if record else None


# ============================================================
# ATUALIZAR CASO
# ============================================================

def update_case(tx, caso_id, data, user_id):

    # Primeiro buscamos o caso atual.
    # Isso permite registrar o que foi alterado.
    old_query = """
    MATCH (c:Caso {id: $casoId})

    RETURN c {
        .id,
        .nome,
        .descricao,
        .status,
        .prioridade,
        .enderecoCep,
        .enderecoLogradouro,
        .enderecoNumero,
        .enderecoBairro,
        .enderecoCidade,
        .enderecoEstado,
        dataOcorrencia: toString(c.dataOcorrencia)
    } AS caso
    """

    old_result = tx.run(
        old_query,
        casoId=caso_id
    )

    old_record = old_result.single()

    if not old_record:
        raise Exception("Caso não encontrado")

    old_case = old_record["caso"]

    # Atualiza
    query = """
    MATCH (c:Caso {id: $casoId})

    SET
        c.nome = $nome,
        c.descricao = $descricao,
        c.status = $status,
        c.prioridade = $prioridade,

        c.enderecoCep = $enderecoCep,
        c.enderecoLogradouro = $enderecoLogradouro,
        c.enderecoNumero = $enderecoNumero,
        c.enderecoBairro = $enderecoBairro,
        c.enderecoCidade = $enderecoCidade,
        c.enderecoEstado = $enderecoEstado,

        c.dataOcorrencia = date($dataOcorrencia),

        c.atualizadoEm = datetime()

    RETURN c {
        .id,
        .nome,
        .descricao,
        .status,
        .prioridade,

        .enderecoCep,
        .enderecoLogradouro,
        .enderecoNumero,
        .enderecoBairro,
        .enderecoCidade,
        .enderecoEstado,

        dataOcorrencia: toString(c.dataOcorrencia),
        atualizadoEm: toString(c.atualizadoEm)
    } AS caso
    """

    result = tx.run(
        query,
        casoId=caso_id,
        **data
    )

    record = result.single()

    if not record:
        raise Exception("Caso não encontrado")

    caso = record["caso"]

    # Descobre quais campos mudaram
    changed_fields = []

    fields_to_compare = [
        "nome",
        "descricao",
        "status",
        "prioridade",
        "enderecoCep",
        "enderecoLogradouro",
        "enderecoNumero",
        "enderecoBairro",
        "enderecoCidade",
        "enderecoEstado",
        "dataOcorrencia",
    ]

    for field in fields_to_compare:
        old_value = old_case.get(field)
        new_value = caso.get(field)

        if old_value != new_value:
            changed_fields.append({
                "campo": field,
                "antes": old_value,
                "depois": new_value
            })
    # HISTÓRICO
    if user_id and changed_fields:
        create_history(
            tx=tx,
            user_id=user_id,
            caso_id=caso_id,
            action="UPDATE",
            entity_type="CASO",
            entity_id=caso_id,
            entity_name=caso["nome"],
            valor_novo=changed_fields,
        )

    return caso


# ============================================================
# DELETAR CASO
# ============================================================

def delete_case(tx, caso_id, user_id=None):
    """
    Exclui o caso e TODOS os nós que pertencem a ele, na mesma transação:
    suspeitos, evidências, contatos, análises probabilísticas, ações
    investigativas e o histórico do caso. As relações com usuários
    (RESPONSAVEL_POR / TEM_ACESSO / REALIZOU) saem junto com o DETACH, mas os
    usuários em si nunca são apagados.

    Obs.: o histórico do caso é excluído junto com ele (pertence ao caso),
    por isso não é gravado um registro "Caso excluído".
    """

    query = """
    MATCH (c:Caso {id: $casoId})

    OPTIONAL MATCH (c)-[:TEM_SUSPEITO|TEM_EVIDENCIA|TEM_CONTATO|TEM_ANALISE|TEM_ACAO]->(filho)
    WITH c, collect(DISTINCT filho) AS filhos

    OPTIONAL MATCH (h:HistoricoCaso)-[:REFERENTE_A]->(c)
    WITH c, filhos, collect(DISTINCT h) AS historico

    FOREACH (n IN filhos | DETACH DELETE n)
    FOREACH (n IN historico | DETACH DELETE n)
    DETACH DELETE c

    RETURN $casoId AS casoId
    """

    result = tx.run(
        query,
        casoId=caso_id
    )

    deleted_record = result.single()

    if not deleted_record:
        raise Exception("Caso não encontrado")

    return {
        "deleted": True,
        "casoId": caso_id
    }


# ============================================================
# PERFIL ESTIMADO
# ============================================================

def get_estimated_profile(tx, caso_id):

    query = """
    MATCH (c:Caso {id: $casoId})

    RETURN
        c.perfilEstimadoComportamento AS comportamento,
        c.perfilEstimadoAgressividade AS agressividade,
        c.perfilEstimadoProximidade AS proximidade,
        c.perfilEstimadoConexoesSociais AS conexoesSociais,
        c.perfilEstimadoNivelConfissao AS nivelConfissao,
        c.perfilEstimadoAtualizadoEm AS atualizadoEm
    """

    record = tx.run(
        query,
        casoId=caso_id
    ).single()

    if not record:
        raise Exception("Caso não encontrado")

    return _estimated_profile_response(
        caso_id,
        record
    )


# ============================================================
# ATUALIZAR PERFIL ESTIMADO
# ============================================================

def set_estimated_profile(
    tx,
    caso_id,
    user_id,
    data
):

    query = """
    MATCH (c:Caso {id: $casoId})

    SET
        c.perfilEstimadoComportamento = $comportamento,
        c.perfilEstimadoAgressividade = $agressividade,
        c.perfilEstimadoProximidade = $proximidade,
        c.perfilEstimadoConexoesSociais = $conexoesSociais,
        c.perfilEstimadoNivelConfissao = $nivelConfissao,

        c.perfilEstimadoAtualizadoEm = datetime(),
        c.perfilEstimadoAtualizadoPor = $userId

    RETURN
        c.perfilEstimadoComportamento AS comportamento,
        c.perfilEstimadoAgressividade AS agressividade,
        c.perfilEstimadoProximidade AS proximidade,
        c.perfilEstimadoConexoesSociais AS conexoesSociais,
        c.perfilEstimadoNivelConfissao AS nivelConfissao,
        c.perfilEstimadoAtualizadoEm AS atualizadoEm
    """

    record = tx.run(
        query,
        casoId=caso_id,
        userId=user_id,
        **data
    ).single()

    if not record:
        raise Exception("Caso não encontrado")

    # HISTÓRICO
    create_history(
        tx=tx,
        user_id=user_id,
        caso_id=caso_id,
        action="UPDATE",
        entity_type="PERFIL_ESTIMADO",
        entity_id=caso_id,
        entity_name="Perfil estimado",
        details="Perfil estimado do caso atualizado",
    )

    return _estimated_profile_response(
        caso_id,
        record
    )


# ============================================================
# CAMPOS DO PERFIL ESTIMADO
# ============================================================

_ESTIMATED_PROFILE_FIELDS = (
    "comportamento",
    "agressividade",
    "proximidade",
    "conexoesSociais",
    "nivelConfissao",
)


# ============================================================
# RESPOSTA DO PERFIL ESTIMADO
# ============================================================

def _estimated_profile_response(caso_id, record):

    perfil = {
        field: record[field]
        for field in _ESTIMATED_PROFILE_FIELDS
    }

    definido = all(
        value is not None
        for value in perfil.values()
    )

    return {
        "casoId": caso_id,

        "perfil": (
            perfil
            if definido
            else None
        ),

        "atualizadoEm": (
            str(record["atualizadoEm"])
            if record["atualizadoEm"]
            else None
        ),
    }
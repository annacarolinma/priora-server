def get_case_id_for_suspect(tx, suspect_id: str) -> str | None:
    query = """
    MATCH (c:Caso)-[:TEM_SUSPEITO]->(s:Suspeito {id: $suspectId})
    RETURN c.id AS casoId
    """

    record = tx.run(
        query,
        suspectId=suspect_id
    ).single()

    return record["casoId"] if record else None



def get_suspect_by_id(tx, suspect_id: str):

    query = """
    MATCH (s:Suspeito {id: $suspectId})

    RETURN s {
        .id,
        .nome,
        .idade,
        .fotoUrl,
        .historicoCriminal,
        .caracteristicasCriminais,
        .significanciaTempoLugar,
        .coerenciaInterpessoal,
        .conscienciaForense,
        .crimeSimilarAntes,
        .histDescumprimento,
        .probabilidadeAtual,
        .posicaoRanking,
        .tendencia
    } AS suspeito
    """

    record = tx.run(
        query,
        suspectId=suspect_id
    ).single()

    return record["suspeito"] if record else None



def create_suspect(tx, data):

    query = """
    MATCH (c:Caso {id: $casoId})

    CREATE (s:Suspeito {

        id: randomUUID(),

        nome: $nome,

        idade: $idade,

        fotoUrl: $fotoUrl,

        probabilidadeAtual: 0.0,

        posicaoRanking: null,

        tendencia: 'Estável',

        historicoCriminal: $historicoCriminal,

        caracteristicasCriminais: $caracteristicasCriminais,

        significanciaTempoLugar: $significanciaTempoLugar,

        coerenciaInterpessoal: $coerenciaInterpessoal,

        conscienciaForense: $conscienciaForense,

        crimeSimilarAntes: $crimeSimilarAntes,

        histDescumprimento: $histDescumprimento,

        criadoEm: datetime(),

        atualizadoEm: datetime()

    })


    CREATE (c)-[:TEM_SUSPEITO {
        adicionadoEm: datetime()
    }]->(s)


    RETURN s {

        .id,

        .nome,

        .idade,

        .fotoUrl,

        .probabilidadeAtual,

        .posicaoRanking,

        .tendencia

    } AS suspeito
    """

    result = tx.run(
        query,
        **data
    )

    record = result.single()

    if not record:
        raise Exception("Caso não encontrado")

    return record["suspeito"]



def list_suspects_by_case(tx, caso_id):

    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_SUSPEITO]->(s:Suspeito)

    OPTIONAL MATCH (s)<-[:VINCULA]-(e:Evidencia)

    RETURN

        s.posicaoRanking AS posicaoRanking,

        s.id AS id,

        s.nome AS nome,

        s.idade AS idade,

        s.fotoUrl AS fotoUrl,

        s.probabilidadeAtual AS probabilidadeAtual,

        s.tendencia AS tendencia,

        s.historicoCriminal AS historicoCriminal,

        s.caracteristicasCriminais AS caracteristicasCriminais,

        s.significanciaTempoLugar AS significanciaTempoLugar,

        s.coerenciaInterpessoal AS coerenciaInterpessoal,

        s.conscienciaForense AS conscienciaForense,

        s.crimeSimilarAntes AS crimeSimilarAntes,

        s.histDescumprimento AS histDescumprimento,

        count(e) AS qtdEvidencias,

        collect(DISTINCT e {.id, .nome, .tipo, .status}) AS evidencias

    ORDER BY s.probabilidadeAtual DESC
    """

    result = tx.run(
        query,
        casoId=caso_id
    )

    return [
        record.data()
        for record in result
    ]



def update_suspect_ranking(tx, caso_id):

    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_SUSPEITO]->(s:Suspeito)

    WITH s
    ORDER BY s.probabilidadeAtual DESC

    WITH collect(s) AS ranking

    UNWIND range(0, size(ranking)-1) AS i

    WITH ranking[i] AS s, i+1 AS pos


    SET 
        s.posicaoRanking = pos,
        s.atualizadoEm = datetime()


    RETURN

        s.id AS id,

        s.nome AS nome,

        s.posicaoRanking AS posicaoRanking,

        s.probabilidadeAtual AS probabilidadeAtual


    ORDER BY s.posicaoRanking ASC
    """

    result = tx.run(
        query,
        casoId=caso_id
    )

    return [
        record.data()
        for record in result
    ]



def update_suspect(tx, suspect_id, data):

    query = """
    MATCH (s:Suspeito {id: $suspectId})


    SET

        s.nome = $nome,

        s.idade = $idade,

        s.fotoUrl = $fotoUrl,

        s.historicoCriminal = $historicoCriminal,

        s.caracteristicasCriminais = $caracteristicasCriminais,

        s.significanciaTempoLugar = $significanciaTempoLugar,

        s.coerenciaInterpessoal = $coerenciaInterpessoal,

        s.conscienciaForense = $conscienciaForense,

        s.crimeSimilarAntes = $crimeSimilarAntes,

        s.histDescumprimento = $histDescumprimento,

        s.atualizadoEm = datetime()


    RETURN s {

        .id,

        .nome,

        .idade,

        .fotoUrl,

        .historicoCriminal,

        .caracteristicasCriminais,

        .significanciaTempoLugar,

        .coerenciaInterpessoal,

        .conscienciaForense,

        .crimeSimilarAntes,

        .histDescumprimento,

        .probabilidadeAtual,

        .posicaoRanking,

        .tendencia

    } AS suspeito
    """

    result = tx.run(
        query,
        suspectId=suspect_id,
        **data
    )

    record = result.single()

    if not record:
        raise Exception("Suspeito não encontrado")

    return record["suspeito"]



def delete_suspect(tx, caso_id, suspect_id):

    query = """
    MATCH 
        (c:Caso {id: $casoId})
        -[r:TEM_SUSPEITO]->
        (s:Suspeito {id: $suspectId})


    OPTIONAL MATCH 
        (e:Evidencia)-[v:VINCULA]->(s)


    DELETE v


    WITH c,r,s


    OPTIONAL MATCH
        (s)-[rel]-()


    DELETE rel


    WITH r,s


    DELETE r,s


    RETURN $suspectId AS suspectId
    """

    result = tx.run(
        query,
        casoId=caso_id,
        suspectId=suspect_id
    )


    record = result.single()


    if not record:
        raise Exception(
            "Suspeito não encontrado neste caso"
        )


    return {
        "deleted": True,
        "suspectId": suspect_id
    }
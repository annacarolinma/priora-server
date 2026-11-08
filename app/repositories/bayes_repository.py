from app.bayes.model import (
    Suspect,
    Evidence,
    EvidenceType,
    EvidenceStatus,
    SuspectResult,
)


def get_previous_results_for_bayes(tx, caso_id):
    """
    Reconstrói um `previous_results` mínimo a partir do último
    `probabilidadeAtual` persistido em cada suspeito, para que o motor
    bayesiano consiga calcular a tendência (Alta/Baixa/Estável) real
    comparando com o cálculo anterior, em vez de sempre "Estável".

    Só os campos suspect.id e probability_pct são lidos por
    BayesianNetwork._compute_trend, então os demais campos do
    SuspectResult ficam com valores neutros (não são usados).
    """
    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_SUSPEITO]->(s:Suspeito)
    WHERE s.probabilidadeAtual IS NOT NULL
    RETURN s.id AS id, s.probabilidadeAtual AS probabilidadeAtual
    """
    result = tx.run(query, casoId=caso_id)

    return [
        SuspectResult(
            suspect=Suspect(id=record["id"], name=""),
            prior=0.0,
            p_e_given_h=0.0,
            numerator=0.0,
            p_h_given_e=0.0,
            probability_pct=record["probabilidadeAtual"],
            uncertainty_pct=0.0,
        )
        for record in result
    ]


def get_suspects_for_bayes(tx, caso_id):
    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_SUSPEITO]->(s:Suspeito)
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
        .histDescumprimento
    } AS suspeito
    ORDER BY s.criadoEm ASC
    """

    result = tx.run(query, casoId=caso_id)

    suspects = []

    for record in result:
        s = record["suspeito"]

        suspects.append(
            Suspect(
                id=s["id"],
                name=s["nome"],
                age=s.get("idade") or 0,
                photo_url=s.get("fotoUrl"),
                criminal_history=s.get("historicoCriminal") or 50.0,
                criminal_characteristics=s.get("caracteristicasCriminais") or 50.0,
                time_place_significance=s.get("significanciaTempoLugar") or 50.0,
                interpersonal_coherence=s.get("coerenciaInterpessoal") or 50.0,
                forensic_awareness=s.get("conscienciaForense") or 50.0,
                crime_before=s.get("crimeSimilarAntes") or "Não sei",
                non_compliance=s.get("histDescumprimento") or "Não sei",
            )
        )

    return suspects


def get_evidences_for_bayes(tx, caso_id):
    """
    Uma evidência compartilhada entre N suspeitos deve virar UM único
    Evidence com um suspect_links = {suspeito_id: pesoVinculo} contendo
    todos os N vínculos, para que o modelo bayesiano calcule corretamente
    o fator de exclusividade (1/|S|) e o pesoVinculo individual de cada
    suspeito (VINCULA é uma relação por par evidência↔suspeito).
    """
    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_EVIDENCIA]->(e:Evidencia)
    OPTIONAL MATCH (e)-[v:VINCULA]->(s:Suspeito)
    WITH e, collect(
        CASE WHEN s IS NOT NULL
            THEN { suspeitoId: s.id, pesoVinculo: v.pesoVinculo }
            ELSE NULL
        END
    ) AS vinculosRaw
    RETURN e {
        .id, .nome, .tipo, .status,
        .pesoCondicional, .dataColeta, .descricao
    } AS evidencia,
    [x IN vinculosRaw WHERE x IS NOT NULL] AS vinculos
    ORDER BY e.criadoEm ASC
    """

    result = tx.run(query, casoId=caso_id)
    evidences = []

    for record in result:
        e = record["evidencia"]
        vinculos = record["vinculos"]

        if not vinculos:
            continue

        suspect_links = {
            v["suspeitoId"]: float(v["pesoVinculo"] if v["pesoVinculo"] is not None else 1.0)
            for v in vinculos
        }

        evidences.append(
            Evidence(
                id=e["id"],
                name=e["nome"],
                type=EvidenceType(e["tipo"]),
                status=EvidenceStatus(e["status"]),
                reliability=float(e.get("pesoCondicional") or 0.5),
                suspect_links=suspect_links,
                date=str(e["dataColeta"]) if e.get("dataColeta") else "",
                description=e.get("descricao") or "",
            )
        )

    return evidences

def save_bayes_results(tx, caso_id, ranking, case_uncertainty):
    query_suspects = """
    UNWIND $ranking AS r
    MATCH (s:Suspeito {id: r.suspect_id})
    SET s.probabilidadeAtual = r.probability_pct,
        s.posicaoRanking     = r.position,
        s.tendencia          = r.trend,
        s.atualizadoEm       = datetime()
    """
    tx.run(query_suspects, casoId=caso_id, ranking=ranking)

    query_case = """
    MATCH (c:Caso {id: $casoId})
    SET c.incerteza    = $incerteza,
        c.atualizadoEm = datetime()
    """
    tx.run(query_case, casoId=caso_id, incerteza=case_uncertainty)


def save_analysis_snapshot(tx, caso_id, ranking):
    """
    Persiste o snapshot de cada cálculo bayesiano como um nó :AnaliseProb
    (seção 15.2.6 da documentação), ligado ao caso via :TEM_ANALISE e ao
    suspeito avaliado via :AVALIA. Cada chamada cria um novo conjunto de
    nós (histórico), nunca sobrescreve um snapshot anterior.
    """
    denominator = sum(r["numerator"] for r in ranking) or 1.0

    query = """
    UNWIND $ranking AS r
    MATCH (c:Caso {id: $casoId})
    MATCH (s:Suspeito {id: r.suspect_id})
    CREATE (a:AnaliseProb {
        id:              randomUUID(),
        prior:           r.prior,
        pEH:             r.p_e_given_h,
        numerator:       r.numerator,
        denominator:     $denominator,
        posterior:       r.p_h_given_e,
        probabilityPct:  r.probability_pct,
        uncertaintyPct:  r.uncertainty_pct,
        position:        r.position,
        calculadoEm:     datetime()
    })
    CREATE (c)-[:TEM_ANALISE]->(a)
    CREATE (a)-[:AVALIA]->(s)
    """
    tx.run(query, casoId=caso_id, ranking=ranking, denominator=denominator)
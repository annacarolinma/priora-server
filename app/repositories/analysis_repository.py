from app.bayes.model import (
    BayesianNetwork,
    Suspect,
    Evidence,
    EvidenceType,
    evidence_type,
    EvidenceStatus,
    evidence_contribution,
)

def generate_analysis(tx, data):

    caso_id = data["casoId"]
    user_id = data["userId"]

    suspects_raw = load_suspects(tx, caso_id)

    evidences_raw = load_evidences(tx, caso_id)

    result = build_analysis(
        caso_id,
        suspects_raw,
        evidences_raw,
    )

    return result.to_dict()


def get_case_uncertainty_evolution(tx, caso_id):
    """
    Evolução da incerteza média do caso ao longo do tempo, com base nos
    snapshots :AnaliseProb gravados a cada recálculo bayesiano
    (ver app.repositories.bayes_repository.save_analysis_snapshot).
    """
    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_ANALISE]->(a:AnaliseProb)
    WITH a.calculadoEm AS calculadoEm, avg(a.uncertaintyPct) AS incerteza
    RETURN toString(calculadoEm) AS calculadoEm, incerteza
    ORDER BY calculadoEm ASC
    """

    result = tx.run(query, casoId=caso_id)
    return [record.data() for record in result]


def get_suspect_history(tx, suspeito_id):
    """
    Histórico de probabilidade posterior de um suspeito ao longo do
    tempo, com base nos snapshots :AnaliseProb ligados a ele via :AVALIA.
    """
    query = """
    MATCH (a:AnaliseProb)-[:AVALIA]->(s:Suspeito {id: $suspeitoId})
    RETURN
        a.probabilityPct AS probabilidade,
        toString(a.calculadoEm) AS data,
        a.position AS posicao
    ORDER BY a.calculadoEm ASC
    """

    result = tx.run(query, suspeitoId=suspeito_id)
    return [record.data() for record in result]


def get_suspect_analysis(tx, caso_id, suspeito_id):
    
    query = """
    MATCH (c:Caso {id: $casoId})-[:TEM_SUSPEITO]->(s:Suspeito {id: $suspeitoId})

    OPTIONAL MATCH (e:Evidencia)-[v:VINCULA]->(s)

    WITH c, s, collect(
        CASE
           WHEN e IS NOT NULL THEN {
                id: e.id,
                nome: e.nome,
                tipo: e.tipo,
                status: e.status,

                pesoCondicional: e.pesoCondicional,
                pesoVinculo: coalesce(v.pesoVinculo, 1.0),
                efeito: coalesce(v.efeito, 'Incrimina'),

                pesoFinal:
                    e.pesoCondicional *
                    coalesce(v.pesoVinculo, 1.0),

                // todos os suspeitos ligados à evidência (fator de exclusividade)
                suspectIds: [(e)-[:VINCULA]->(x:Suspeito) | x.id],
                // suspeitos que a evidência incrimina (base do fator de exclusividade)
                nIncriminados: size([(e)-[y:VINCULA]->(:Suspeito) WHERE coalesce(y.efeito, 'Incrimina') <> 'Inocenta' | 1]),

                dataColeta: toString(e.dataColeta),
                descricao: e.descricao
            }
            ELSE NULL
        END
    ) AS todasEvidencias

    WITH c, s,
        [ev IN todasEvidencias WHERE ev IS NOT NULL] AS evidencias

    MATCH (c)-[:TEM_SUSPEITO]->(todos:Suspeito)

    WITH
        s,
        evidencias,
        count(todos) AS nSuspeitos

    RETURN {
        id: s.id,
        nome: s.nome,
        fotoUrl: s.fotoUrl,
        probabilidadeAtual: s.probabilidadeAtual,
        posicaoRanking: s.posicaoRanking,
        tendencia: s.tendencia,
        nSuspeitos: nSuspeitos,
        evidencias: evidencias
    } AS suspeito
    """

    record = tx.run(
        query,
        casoId=caso_id,
        suspeitoId=suspeito_id
    ).single()

    if not record:
        raise Exception("Suspeito não encontrado")

    suspeito = record["suspeito"]

    # contribuição de cada evidência, calculada pela MESMA função do modelo
    for ev in suspeito["evidencias"]:
        ev["contribuicao"] = round(
            evidence_contribution(
                ev["pesoCondicional"],
                ev["pesoVinculo"],
                ev["nIncriminados"],
                ev["efeito"],
            ),
            6,
        )

    # executa o mesmo modelo bayesiano usado na análise
    suspects_raw = load_suspects(tx, caso_id)
    evidences_raw = load_evidences(tx, caso_id)

    analysis = build_analysis(
        caso_id,
        suspects_raw,
        evidences_raw
    )

    # encontra o resultado do suspeito dentro do ranking
    bayes = next(
        (
            r for r in analysis.ranking
            if r.suspect.id == suspeito_id
        ),
        None
    )

    if not bayes:
        raise Exception("Resultado bayesiano não encontrado")
    
    denominator = sum(r.numerator for r in analysis.ranking)

    suspeito["bayes"] = {
        "prior": round(bayes.prior, 6),
        "pEH": round(bayes.p_e_given_h, 6),
        "numerator": round(bayes.numerator, 6),
        "denominator": round(denominator, 6),
        "posterior": round(bayes.p_h_given_e, 6),
        "probabilityPct": round(bayes.probability_pct, 2),
        "uncertaintyPct": round(bayes.uncertainty_pct, 2),
        "position": bayes.position
    }

    return suspeito

def load_suspects(tx, caso_id):
    query = """
    MATCH (:Caso {id:$casoId})-[:TEM_SUSPEITO]->(s:Suspeito)

    RETURN
        s.id AS id,
        s.nome AS nome,
        s.idade AS idade,
        s.fotoUrl AS fotoUrl
    """

    result = tx.run(query, casoId=caso_id)

    return [r.data() for r in result]


def load_evidences(tx, caso_id):
    query = """
    MATCH (:Caso {id:$casoId})-[:TEM_EVIDENCIA]->(e:Evidencia)

    OPTIONAL MATCH (e)-[v:VINCULA]->(s:Suspeito)

    WITH e, collect(
        CASE WHEN s IS NOT NULL
            THEN { suspeitoId: s.id, pesoVinculo: v.pesoVinculo, efeito: coalesce(v.efeito, 'Incrimina') }
            ELSE NULL
        END
    ) AS vinculosRaw

    RETURN
        e.id AS id,
        e.nome AS nome,
        e.tipo AS tipo,
        e.status AS status,
        e.pesoCondicional AS peso,
        [x IN vinculosRaw WHERE x IS NOT NULL] AS vinculos,
        toString(e.dataColeta) AS dataColeta,
        e.descricao AS descricao
    """

    result = tx.run(query, casoId=caso_id)

    return [r.data() for r in result]


def build_analysis(caso_id, suspects_raw, evidences_raw):

    suspects = [
        Suspect(
            id=s["id"],
            name=s["nome"],
            age=s.get("idade") or 0,
            photo_url=s.get("fotoUrl"),
        )
        for s in suspects_raw
    ]

    evidences = [
        Evidence(
            id=e["id"],
            name=e["nome"],
            type=evidence_type(e["tipo"]),
            status=EvidenceStatus(e["status"]),
            reliability=e["peso"],
            suspect_links={
                v["suspeitoId"]: (v["pesoVinculo"] if v["pesoVinculo"] is not None else 1.0)
                for v in e["vinculos"]
            },
            suspect_effects={v["suspeitoId"]: v.get("efeito") or "Incrimina" for v in e["vinculos"]},
            date=e["dataColeta"] or "",
            description=e["descricao"] or "",
        )
        for e in evidences_raw
        if e["vinculos"]
    ]

    network = BayesianNetwork()

    analysis = network.run(
        case_id=caso_id,
        suspects=suspects,
        evidences=evidences,
    )

    return analysis
"""
Priorização de Ações Investigativas (RF11).

Metodologia: as ações candidatas e seus scores são inteiramente
derivados dos suspeitos e evidências já cadastrados no caso — não há
nenhuma entrada manual do investigador. A "recompensa" de cada ação é o
ganho de informação esperado (EIG), medido como redução da entropia de
Shannon (SHANNON, 1948) sobre a distribuição posterior dos suspeitos.

Essa abordagem segue o framework de "Expected Value of Information"
(EVOI) da teoria da decisão bayesiana (LINDLEY, 1956; HOWARD, 1966),
formalizado para avaliação de evidência forense por GITTELSON & TARONI
(2025) — "vale a pena processar/testar esta evidência?" — e para
priorização de coleta de dados em síntese de evidências bayesiana por
JACKSON et al. (2019), que definem o EVPPI como a redução esperada de
incerteza de decisão ao se aprender um parâmetro. O princípio de
selecionar a próxima ação pelo ganho de informação esperado também é a
base das estratégias de "active learning" (SETTLES, 2009).

O "esforço" de cada ação NÃO é uma grandeza probabilística: segue a
separação clássica de ação/estado/utilidade da teoria da decisão
(GITTELSON & TARONI, 2025), na qual o custo de uma ação é um componente
distinto do seu valor informacional. Aqui ele é aproximado por um proxy
operacional (estágio da evidência na cadeia de custódia, ou quantidade
de evidências já vinculadas ao suspeito).
"""

import math

from app.bayes.model import BayesianNetwork, shannon_entropy_bits
from app.repositories.bayes_repository import (
    get_suspects_for_bayes,
    get_evidences_for_bayes,
)

PENDING_EVIDENCE_STATUSES = {"Em análise", "Enviada a perícia"}

# Proxy operacional de esforço por estágio da evidência na cadeia de
# custódia (não é uma grandeza probabilística — ver docstring do módulo).
EFFORT_BY_EVIDENCE_STATUS = {
    "Em análise": 35.0,
    "Enviada a perícia": 70.0,
}

# Ignora contribuições de incerteza desprezíveis (< 1% do total).
MIN_RELEVANT_GAIN_PCT = 1.0


def _impact_level(recompensa_pct: float) -> str:
    if recompensa_pct >= 15:
        return "Alto"
    if recompensa_pct >= 5:
        return "Médio"
    return "Baixo"


def compute_candidate_actions(tx, caso_id: str) -> list[dict]:
    suspects = get_suspects_for_bayes(tx, caso_id)
    if not suspects:
        return []

    evidences = get_evidences_for_bayes(tx, caso_id)

    network = BayesianNetwork()
    base_result = network.run(case_id=caso_id, suspects=suspects, evidences=evidences)
    base_posteriors = [r.p_h_given_e for r in base_result.ranking]
    h_atual = shannon_entropy_bits(base_posteriors)

    candidates: list[dict] = []

    # ── Tipo A: evidências pendentes de confirmação ─────────────────
    # Recompensa = quanta incerteza esta evidência já está resolvendo
    # hoje (EIG = H sem ela − H com ela). Processá-la/confirmá-la
    # preserva esse ganho; deixá-la parada arrisca perdê-lo.
    for evidence in evidences:
        if evidence.status.value not in PENDING_EVIDENCE_STATUSES:
            continue

        remaining = [e for e in evidences if e.id != evidence.id]

        if remaining:
            result_sem = network.run(case_id=caso_id, suspects=suspects, evidences=remaining)
            h_sem = shannon_entropy_bits([r.p_h_given_e for r in result_sem.ranking])
        else:
            # sem nenhuma evidência restante, a distribuição é uniforme
            h_sem = shannon_entropy_bits([1.0 / len(suspects)] * len(suspects))

        eig = max(0.0, h_sem - h_atual)
        recompensa_pct = round((eig / h_sem) * 100, 1) if h_sem > 0 else 0.0

        if recompensa_pct < MIN_RELEVANT_GAIN_PCT:
            continue

        candidates.append({
            "sourceKey": f"ev:{evidence.id}",
            "tipo": "Evidencia",
            "titulo": f"Processar evidência pendente: {evidence.name}",
            "metricaLabel": "Ganho de informação estimado (entropia)",
            "metricaValor": recompensa_pct,
            "recompensa": recompensa_pct,
            "esforco": EFFORT_BY_EVIDENCE_STATUS.get(evidence.status.value, 50.0),
            "impacto": _impact_level(recompensa_pct),
        })

    # ── Tipo B: suspeitos que mais contribuem para a incerteza ──────
    # Recompensa = autoinformação do suspeito (-pᵢ·log2(pᵢ)) como fração
    # da entropia total — a decomposição padrão de Shannon da incerteza
    # em contribuições por resultado.
    qtd_evidencias_por_suspeito = {
        s.id: sum(1 for e in evidences if s.id in e.suspect_links)
        for s in suspects
    }

    for suspect, posterior in zip(suspects, base_posteriors):
        if posterior <= 0:
            continue

        self_info = -posterior * math.log2(posterior)
        recompensa_pct = round((self_info / h_atual) * 100, 1) if h_atual > 0 else 0.0

        if recompensa_pct < MIN_RELEVANT_GAIN_PCT:
            continue

        qtd = qtd_evidencias_por_suspeito.get(suspect.id, 0)
        esforco = max(10.0, min(90.0, 100.0 - qtd * 15.0))

        candidates.append({
            "sourceKey": f"sus:{suspect.id}",
            "tipo": "Suspeito",
            "titulo": f"Aprofundar investigação sobre {suspect.name}",
            "metricaLabel": "Contribuição para a incerteza do caso (entropia)",
            "metricaValor": recompensa_pct,
            "recompensa": recompensa_pct,
            "esforco": esforco,
            "impacto": _impact_level(recompensa_pct),
        })

    candidates.sort(key=lambda c: c["recompensa"], reverse=True)
    return candidates


def upsert_and_list_actions(tx, caso_id: str) -> list[dict]:
    """
    Recalcula os candidatos e sincroniza com os nós :AcaoInvestigativa
    existentes: cria os novos, atualiza os scores dos que já existem
    (preservando o status definido manualmente pelo investigador) e
    remove sugestões que deixaram de ser relevantes E que o investigador
    ainda não tocou (status 'Sugerida'). Ações excluídas pelo investigador
    continuam gravadas (marcadas como `excluida`) para não serem sugeridas
    de novo, mas não são listadas.
    """
    candidates = compute_candidate_actions(tx, caso_id)

    if candidates:
        query = """
        UNWIND $candidates AS c
        MATCH (caso:Caso {id: $casoId})
        MERGE (caso)-[:TEM_ACAO]->(a:AcaoInvestigativa {sourceKey: c.sourceKey})
        ON CREATE SET
            a.id = randomUUID(),
            a.status = 'Sugerida',
            a.criadoEm = datetime()
        SET
            a.tipo = c.tipo,
            a.titulo = c.titulo,
            a.metricaLabel = c.metricaLabel,
            a.metricaValor = c.metricaValor,
            a.recompensa = c.recompensa,
            a.esforco = c.esforco,
            a.impacto = c.impacto,
            a.atualizadoEm = datetime()
        WITH a
        WHERE coalesce(a.excluida, false) = false
        RETURN a {
            .id, .tipo, .titulo, .status, .impacto,
            .metricaLabel, .metricaValor, .recompensa, .esforco
        } AS acao
        """
        result = tx.run(query, casoId=caso_id, candidates=candidates)
        actions = [record["acao"] for record in result]
    else:
        actions = []

    valid_keys = [c["sourceKey"] for c in candidates]
    cleanup_query = """
    MATCH (:Caso {id: $casoId})-[r:TEM_ACAO]->(a:AcaoInvestigativa)
    WHERE NOT a.sourceKey IN $validKeys AND a.status = 'Sugerida'
    DELETE r, a
    """
    tx.run(cleanup_query, casoId=caso_id, validKeys=valid_keys)

    actions.sort(key=lambda a: a["recompensa"], reverse=True)
    return actions


def get_case_id_for_action(tx, action_id: str) -> str | None:
    query = """
    MATCH (c:Caso)-[:TEM_ACAO]->(a:AcaoInvestigativa {id: $actionId})
    RETURN c.id AS casoId
    """
    record = tx.run(query, actionId=action_id).single()
    return record["casoId"] if record else None


def update_action_status(tx, action_id: str, new_status: str) -> dict:
    query = """
    MATCH (a:AcaoInvestigativa {id: $actionId})
    SET a.status = $status, a.atualizadoEm = datetime()
    RETURN a {
        .id, .tipo, .titulo, .status, .impacto,
        .metricaLabel, .metricaValor, .recompensa, .esforco
    } AS acao
    """
    record = tx.run(query, actionId=action_id, status=new_status).single()
    if not record:
        raise Exception("Ação não encontrada")
    return record["acao"]


def get_action_for_exclusion(tx, action_id: str) -> dict | None:
    record = tx.run(
        """
        MATCH (c:Caso)-[:TEM_ACAO]->(a:AcaoInvestigativa {id: $actionId})
        RETURN c.id AS casoId, a.status AS status, a.titulo AS titulo
        """,
        actionId=action_id,
    ).single()
    return record.data() if record else None


def exclude_action(tx, action_id: str) -> None:
    """Exclui a ação da lista. Não apaga o nó: a ação seria sugerida de novo no próximo recálculo."""
    tx.run(
        "MATCH (a:AcaoInvestigativa {id: $actionId}) SET a.excluida = true, a.excluidaEm = datetime()",
        actionId=action_id,
    )

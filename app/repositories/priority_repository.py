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
from dataclasses import replace

from app.bayes.model import BayesianNetwork, shannon_entropy_bits
from app.repositories.bayes_repository import (
    get_suspects_for_bayes,
    get_evidences_for_bayes,
)

PENDING_EVIDENCE_STATUSES = {"Em análise", "Enviada a perícia"}
COLLECTED_STATUS = "Coletada"

# Proxy operacional de esforço por estágio da evidência na cadeia de
# custódia (não é uma grandeza probabilística — ver docstring do módulo).
EFFORT_BY_EVIDENCE_STATUS = {
    "Em análise": 35.0,
    "Enviada a perícia": 70.0,
}
EFFORT_COLLECTED = 25.0          # encaminhar uma evidência já coletada
EFFORT_REVIEW = 40.0             # reavaliar/corroborar evidência fraca
EFFORT_DIFFERENTIATE = 60.0      # achar evidência que separe dois suspeitos
EFFORT_NO_EVIDENCE_CASE = 20.0   # cadastrar as primeiras evidências

# Evidência de baixa confiabilidade (peso da evidência) e valor assumido
# se ela for corroborada.
LOW_RELIABILITY_THRESHOLD = 0.4
CONFIRMED_RELIABILITY = 0.9

# Empate no topo: diferença máxima (em pontos percentuais) entre o 1º e o 2º.
TIE_MARGIN_PP = 10.0

# Ignora contribuições de incerteza desprezíveis (< 1% do total).
MIN_RELEVANT_GAIN_PCT = 1.0


def _impact_level(recompensa_pct: float) -> str:
    if recompensa_pct >= 15:
        return "Alto"
    if recompensa_pct >= 5:
        return "Médio"
    return "Baixo"


def _h_term(p: float) -> float:
    """Parcela -p·log2(p) da entropia de Shannon (0 quando p = 0)."""
    return -p * math.log2(p) if p > 0 else 0.0


def _entropy_with(network, caso_id, suspects, evidences) -> float:
    result = network.run(case_id=caso_id, suspects=suspects, evidences=evidences)
    return shannon_entropy_bits([r.p_h_given_e for r in result.ranking])


def compute_candidate_actions(tx, caso_id: str) -> list[dict]:
    suspects = get_suspects_for_bayes(tx, caso_id)
    if not suspects:
        return []

    evidences = [
        e for e in get_evidences_for_bayes(tx, caso_id)
        if e.status.value != "Descartada"
    ]

    network = BayesianNetwork()
    base_result = network.run(case_id=caso_id, suspects=suspects, evidences=evidences)
    base_posteriors = [r.p_h_given_e for r in base_result.ranking]
    h_atual = shannon_entropy_bits(base_posteriors)

    candidates: list[dict] = []

    # ── Caso sem nenhuma evidência ──────────────────────────────────
    # Toda a incerteza ainda está por tratar: recompensa = 100% (limite
    # superior). Nesse caso, as demais sugestões não fazem sentido.
    if not evidences:
        if len(suspects) < 2:
            return []
        return [{
            "sourceKey": "case:sem-evidencias",
            "tipo": "SemEvidencias",
            "titulo": "Cadastrar as primeiras evidências do caso",
            "metricaLabel": "Incerteza ainda não tratada (entropia)",
            "metricaValor": 100.0,
            "recompensa": 100.0,
            "esforco": EFFORT_NO_EVIDENCE_CASE,
            "impacto": _impact_level(100.0),
        }]

    # ── Tipos A e H: evidência pendente ou apenas coletada ──────────
    # Recompensa = quanta incerteza a evidência já resolve hoje
    # (EIG = H sem ela − H com ela), em % da incerteza sem ela.
    for evidence in evidences:
        status = evidence.status.value
        if status in PENDING_EVIDENCE_STATUSES:
            tipo, prefix = "Evidencia", "ev"
            titulo = f"Processar evidência pendente: {evidence.name}"
            esforco = EFFORT_BY_EVIDENCE_STATUS.get(status, 50.0)
        elif status == COLLECTED_STATUS:
            tipo, prefix = "EvidenciaColetada", "evc"
            titulo = f"Encaminhar para análise a evidência coletada: {evidence.name}"
            esforco = EFFORT_COLLECTED
        else:
            continue

        remaining = [e for e in evidences if e.id != evidence.id]
        if remaining:
            h_sem = _entropy_with(network, caso_id, suspects, remaining)
        else:
            # sem nenhuma evidência restante, a distribuição é uniforme
            h_sem = shannon_entropy_bits([1.0 / len(suspects)] * len(suspects))

        eig = max(0.0, h_sem - h_atual)
        recompensa_pct = round((eig / h_sem) * 100, 1) if h_sem > 0 else 0.0

        if recompensa_pct < MIN_RELEVANT_GAIN_PCT:
            continue

        candidates.append({
            "sourceKey": f"{prefix}:{evidence.id}",
            "tipo": tipo,
            "titulo": titulo,
            "metricaLabel": "Ganho de informação estimado (entropia)",
            "metricaValor": recompensa_pct,
            "recompensa": recompensa_pct,
            "esforco": esforco,
            "impacto": _impact_level(recompensa_pct),
        })

    # ── Tipo E: evidência de baixa confiabilidade ───────────────────
    # Recompensa = quanto a incerteza mudaria se a evidência fosse
    # corroborada (confiabilidade elevada para CONFIRMED_RELIABILITY).
    for evidence in evidences:
        if evidence.reliability >= LOW_RELIABILITY_THRESHOLD or not evidence.suspect_links:
            continue

        confirmed = [
            replace(e, reliability=CONFIRMED_RELIABILITY) if e.id == evidence.id else e
            for e in evidences
        ]
        h_conf = _entropy_with(network, caso_id, suspects, confirmed)
        recompensa_pct = round((abs(h_atual - h_conf) / h_atual) * 100, 1) if h_atual > 0 else 0.0

        if recompensa_pct < MIN_RELEVANT_GAIN_PCT:
            continue

        candidates.append({
            "sourceKey": f"evf:{evidence.id}",
            "tipo": "EvidenciaFraca",
            "titulo": f"Reavaliar ou corroborar a evidência de baixa confiabilidade: {evidence.name}",
            "metricaLabel": "Mudança potencial na incerteza se confirmada (entropia)",
            "metricaValor": recompensa_pct,
            "recompensa": recompensa_pct,
            "esforco": EFFORT_REVIEW,
            "impacto": _impact_level(recompensa_pct),
        })

    # ── Tipo D: dois suspeitos praticamente empatados no topo ───────
    # Recompensa = redução de entropia se uma evidência decisiva separasse
    # os dois (toda a massa dos dois ficaria com um só), em % de H atual.
    ranked = sorted(zip(suspects, base_posteriors), key=lambda x: x[1], reverse=True)
    if len(ranked) >= 2 and h_atual > 0:
        (s1, p1), (s2, p2) = ranked[0], ranked[1]
        if (p1 - p2) * 100 <= TIE_MARGIN_PP:
            ganho = _h_term(p1) + _h_term(p2) - _h_term(p1 + p2)
            recompensa_pct = round((ganho / h_atual) * 100, 1)
            if recompensa_pct >= MIN_RELEVANT_GAIN_PCT:
                a, b = sorted([s1.id, s2.id])
                candidates.append({
                    "sourceKey": f"dif:{a}:{b}",
                    "tipo": "Diferenciar",
                    "titulo": f"Buscar evidência que diferencie {s1.name} de {s2.name}",
                    "metricaLabel": "Ganho potencial ao separar os dois (entropia)",
                    "metricaValor": recompensa_pct,
                    "recompensa": recompensa_pct,
                    "esforco": EFFORT_DIFFERENTIATE,
                    "impacto": _impact_level(recompensa_pct),
                })

    # ── Tipos B e C: suspeitos que mais contribuem para a incerteza ─
    # Recompensa = autoinformação do suspeito (-pᵢ·log2(pᵢ)) como fração
    # da entropia total — a decomposição padrão de Shannon da incerteza
    # em contribuições por resultado. Sem nenhuma evidência vinculada, a
    # sugestão passa a ser buscar evidências (tipo C).
    qtd_evidencias_por_suspeito = {
        s.id: sum(1 for e in evidences if s.id in e.suspect_links)
        for s in suspects
    }

    for suspect, posterior in zip(suspects, base_posteriors):
        if posterior <= 0:
            continue

        recompensa_pct = round((_h_term(posterior) / h_atual) * 100, 1) if h_atual > 0 else 0.0

        if recompensa_pct < MIN_RELEVANT_GAIN_PCT:
            continue

        qtd = qtd_evidencias_por_suspeito.get(suspect.id, 0)
        esforco = max(10.0, min(90.0, 100.0 - qtd * 15.0))

        if qtd == 0:
            tipo, prefix = "SuspeitoSemEvidencia", "sus0"
            titulo = f"Buscar evidências que liguem ou excluam {suspect.name}"
        else:
            tipo, prefix = "Suspeito", "sus"
            titulo = f"Aprofundar investigação sobre {suspect.name}"

        candidates.append({
            "sourceKey": f"{prefix}:{suspect.id}",
            "tipo": tipo,
            "titulo": titulo,
            "metricaLabel": "Contribuição para a incerteza do caso (entropia)",
            "metricaValor": recompensa_pct,
            "recompensa": recompensa_pct,
            "esforco": esforco,
            "impacto": _impact_level(recompensa_pct),
        })

    candidates.sort(key=lambda c: c["recompensa"], reverse=True)
    return candidates


def action_type_catalog() -> list[dict]:
    """
    Explicação de cada tipo de sugestão (quando aparece, quando some,
    recompensa e esforço). Gerada a partir das mesmas constantes usadas no
    cálculo, para o texto nunca divergir do comportamento real.
    """
    gain = f"{MIN_RELEVANT_GAIN_PCT:g}%"
    return [
        {
            "tipo": "SemEvidencias",
            "nome": "Cadastrar as primeiras evidências",
            "quandoAparece": "O caso tem pelo menos dois suspeitos e nenhuma evidência cadastrada. Nesse caso, é a única sugestão.",
            "quandoSome": "Assim que a primeira evidência é cadastrada.",
            "recompensa": "100% (limite superior): toda a incerteza do caso ainda está por tratar.",
            "esforco": f"Fixo em {EFFORT_NO_EVIDENCE_CASE:g}: cadastrar evidências que já existem.",
        },
        {
            "tipo": "Evidencia",
            "nome": "Processar evidência pendente",
            "quandoAparece": f"Uma evidência está \"Em análise\" ou \"Enviada a perícia\" e resolve pelo menos {gain} da incerteza.",
            "quandoSome": f"Quando a evidência muda de status (por exemplo, para \"Custodiada\" ou \"Descartada\") ou quando deixa de resolver {gain} da incerteza.",
            "recompensa": "Quanto de incerteza a evidência já resolve hoje (ganho de informação: entropia sem ela menos entropia com ela, em % da entropia sem ela). Processá-la preserva esse ganho.",
            "esforco": f"Fixo pelo status: {EFFORT_BY_EVIDENCE_STATUS['Em análise']:g} para \"Em análise\" e {EFFORT_BY_EVIDENCE_STATUS['Enviada a perícia']:g} para \"Enviada a perícia\".",
        },
        {
            "tipo": "EvidenciaColetada",
            "nome": "Encaminhar evidência coletada",
            "quandoAparece": f"Uma evidência está apenas \"Coletada\" (ainda não analisada) e resolve pelo menos {gain} da incerteza.",
            "quandoSome": f"Quando a evidência avança de status ou deixa de resolver {gain} da incerteza.",
            "recompensa": "Mesmo cálculo da evidência pendente: quanto de incerteza ela já resolve hoje.",
            "esforco": f"Fixo em {EFFORT_COLLECTED:g}: encaminhar para análise.",
        },
        {
            "tipo": "EvidenciaFraca",
            "nome": "Reavaliar evidência de baixa confiabilidade",
            "quandoAparece": f"O peso da evidência (confiabilidade) é menor que {LOW_RELIABILITY_THRESHOLD:g}, ela está vinculada a algum suspeito e corroborá-la mudaria pelo menos {gain} da incerteza.",
            "quandoSome": "Quando o peso da evidência sobe para o limite ou acima, ou quando ela é descartada.",
            "recompensa": f"Quanto a incerteza mudaria se a evidência fosse corroborada (peso elevado a {CONFIRMED_RELIABILITY:g}), em % da incerteza atual. É uma estimativa da mudança, não do ganho garantido.",
            "esforco": f"Fixo em {EFFORT_REVIEW:g}: reavaliar ou buscar corroboração.",
        },
        {
            "tipo": "Diferenciar",
            "nome": "Diferenciar os dois suspeitos mais prováveis",
            "quandoAparece": f"A diferença de probabilidade entre o 1º e o 2º colocados é de até {TIE_MARGIN_PP:g} pontos percentuais.",
            "quandoSome": "Quando a diferença entre os dois passa desse limite, ou quando o par no topo muda.",
            "recompensa": "Redução de incerteza se uma evidência decisiva separasse os dois (a probabilidade dos dois ficaria com um só), em % da incerteza atual.",
            "esforco": f"Fixo em {EFFORT_DIFFERENTIATE:g}: achar uma evidência que separe os dois.",
        },
        {
            "tipo": "SuspeitoSemEvidencia",
            "nome": "Buscar evidências para um suspeito sem vínculos",
            "quandoAparece": f"O suspeito não tem nenhuma evidência vinculada (e o caso tem evidências) e responde por pelo menos {gain} da incerteza.",
            "quandoSome": "Quando uma evidência é vinculada ao suspeito (passa a valer a sugestão de aprofundar a investigação) ou quando a parcela dele cai abaixo do limite.",
            "recompensa": "Parte da incerteza do caso que vem desse suspeito (-p·log2 p, em % da entropia total).",
            "esforco": "Alto (90): sem evidências vinculadas, não há base para o trabalho. Cai 15 pontos por evidência vinculada, entre 10 e 90.",
        },
        {
            "tipo": "Suspeito",
            "nome": "Aprofundar investigação sobre o suspeito",
            "quandoAparece": f"O suspeito tem pelo menos uma evidência vinculada e responde por pelo menos {gain} da incerteza do caso.",
            "quandoSome": f"Quando a parcela dele cai abaixo de {gain} (por exemplo, quando a probabilidade dele se aproxima de 0).",
            "recompensa": "Parte da incerteza do caso que vem desse suspeito (-p·log2 p, em % da entropia total). Suspeitos mais prováveis costumam render mais.",
            "esforco": "100 menos 15 por evidência já vinculada, entre 10 e 90: quanto mais evidências já ligadas, menor o esforço estimado.",
        },
    ]


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

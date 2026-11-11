from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import reduce
from operator import mul
from typing import Optional


# ─── Enums ────────────────────────────────────────────────────────────────────

class EvidenceType(str, Enum):
    DIGITAL     = "Digital"
    DNA         = "DNA"
    DEPOIMENTO  = "Depoimento"
    DOCUMENTAL  = "Documental"
    FISICA      = "Física"
    AUDIOVISUAL = "Audiovisual"
    BIOLOGICA   = "Biológica"
    MOTIVACAO     = "Motivação"
    ANTECEDENTE   = "Antecedente"
    PERICIAL      = "Pericial"
    TELEFONICA    = "Telefônica"
    COMPORTAMENTO = "Comportamento"
    OUTRA         = "Outra"   # qualquer tipo personalizado


def evidence_type(valor) -> "EvidenceType":
    """Converte o texto salvo na evidência; tipos personalizados viram OUTRA (o tipo não entra no cálculo)."""
    try:
        return EvidenceType(valor)
    except ValueError:
        return EvidenceType.OUTRA


class EvidenceStatus(str, Enum):
    COLETADA    = "Coletada"
    EM_ANALISE  = "Em análise"
    CUSTODIADA  = "Custodiada"
    DESCARTADA  = "Descartada"
    PERICIA = "Enviada a perícia"


class Trend(str, Enum):
    UP     = "Alta"
    DOWN   = "Baixa"
    STABLE = "Estável"


# ─── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class Evidence:
    """
    Representa uma evidência vinculada a um ou mais suspeitos.

    Segue a separação de dois níveis da documentação (seção 16.3):
    - reliability (r): confiabilidade da EVIDÊNCIA em si (pesoCondicional),
      única por evidência, independente de para quem ela aponta.
    - suspect_links (v): força do VÍNCULO entre a evidência e CADA suspeito
      (pesoVinculo), podendo ser diferente para cada suspeito vinculado.

    A contribuição C(Hᵢ, eⱼ) = 1 + (r × v × 1/|S|) usa r e o v específico
    do suspeito Hᵢ.
    """
    id:             str
    name:           str
    type:           EvidenceType
    status:         EvidenceStatus
    reliability:    float               # r ∈ [0.0, 1.0] — pesoCondicional
    suspect_links:  dict[str, float]    # {suspeito_id: pesoVinculo ∈ [0.0, 1.0]}
    # {suspeito_id: "Incrimina" | "Inocenta"}; ausente = Incrimina (compatível com dados antigos)
    suspect_effects: dict[str, str]     = field(default_factory=dict)
    date:           str                 = ""
    description:    str                 = ""

    def __post_init__(self):
        if not (0.0 <= self.reliability <= 1.0):
            raise ValueError(
                f"Evidência '{self.name}': peso da evidência deve estar entre 0.0 e 1.0, "
                f"recebido {self.reliability}."
            )
        for suspect_id, peso_vinculo in self.suspect_links.items():
            if not (0.0 <= peso_vinculo <= 1.0):
                raise ValueError(
                    f"Evidência '{self.name}': peso de vínculo com o suspeito {suspect_id} "
                    f"deve estar entre 0.0 e 1.0, recebido {peso_vinculo}."
                )

    @property
    def suspect_ids(self) -> list[str]:
        return list(self.suspect_links.keys())

    def effect_for(self, suspect_id: str) -> str:
        return self.suspect_effects.get(suspect_id, EFEITO_INCRIMINA)

    @property
    def n_incriminated(self) -> int:
        """Suspeitos que a evidência incrimina (base do fator de exclusividade)."""
        return sum(1 for s in self.suspect_links if self.effect_for(s) != EFEITO_INOCENTA)


@dataclass
class Suspect:
    id:                 str
    name:               str
    age:                int                 = 0
    criminal_history:           float               = 50.0
    criminal_characteristics:     float               = 50.0
    time_place_significance:          float               = 50.0
    interpersonal_coherence: float               = 50.0
    forensic_awareness:   float               = 50.0
    crime_before:       str                 = "Não sei"
    non_compliance:     str                 = "Não sei"
    photo_url:          Optional[str]       = None


@dataclass
class SuspectResult:
    """
    Resultado bayesiano para um suspeito.

    Attributes:
        p_e_given_h:     P(E|Hᵢ) — verossimilhança (produto dos pesos).
                         Será 1.0 se o suspeito não tiver evidências vinculadas.
        numerator:       P(E|Hᵢ) · P(Hᵢ) — antes da normalização global.
        p_h_given_e:     P(Hᵢ|E) — posterior normalizado globalmente ∈ [0,1].
                         Garante Σ = 1.0 entre todos os suspeitos.
    """
    suspect:             Suspect
    prior:               float
    p_e_given_h:         float
    numerator:           float
    p_h_given_e:         float
    probability_pct:     float
    uncertainty_pct:     float
    position:            int                = 0
    trend:               Trend              = Trend.STABLE
    linked_evidences:    list[Evidence]     = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "suspect_id":          self.suspect.id,
            "suspect_name":        self.suspect.name,
            "position":            self.position,
            "prior":               round(self.prior, 6),
            "p_e_given_h":         round(self.p_e_given_h, 6),
            "numerator":           round(self.numerator, 6),
            "p_h_given_e":         round(self.p_h_given_e, 6),
            "probability_pct":     round(self.probability_pct, 2),
            "uncertainty_pct":     round(self.uncertainty_pct, 2),
            "trend":               self.trend.value,
            "linked_evidence_ids": [e.id for e in self.linked_evidences],
        }


@dataclass
class BayesianAnalysisResult:
    case_id:           str
    version:           int
    n_suspects:        int
    n_evidences:       int
    ranking:           list[SuspectResult]
    case_uncertainty:  float
    avg_uncertainty:   float

    def sum_check(self) -> float:
        """Deve retornar 1.0 (ou muito próximo). Use para validação."""
        return sum(r.p_h_given_e for r in self.ranking)

    def to_dict(self) -> dict:
        return {
            "case_id":          self.case_id,
            "version":          self.version,
            "n_suspects":       self.n_suspects,
            "n_evidences":      self.n_evidences,
            "case_uncertainty": round(self.case_uncertainty, 2),
            "avg_uncertainty":  round(self.avg_uncertainty, 2),
            "sum_check":        round(self.sum_check(), 8),   # deve ser 1.0
            "ranking":          [r.to_dict() for r in self.ranking],
        }


# ─── Engine ───────────────────────────────────────────────────────────────────

import math
from typing import List, Optional


EFEITO_INCRIMINA = "Incrimina"
EFEITO_INOCENTA = "Inocenta"


def evidence_contribution(
    reliability: float,
    link_weight: float,
    n_linked: int,
    efeito: str = EFEITO_INCRIMINA,
) -> float:
    """
    Contribuição C de uma evidência para um suspeito (razão de verossimilhança).

    Evidência que INCRIMINA (seção 16.3):  C = 1 + r · v · 1/|S|  (C ≥ 1)
      r = confiabilidade da evidência, v = peso do vínculo com ESTE suspeito e
      |S| = número de suspeitos que a evidência incrimina (fator de exclusividade).

    Evidência que INOCENTA (álibi, contradição):  C = 1 / (1 + r · v)  (C ≤ 1)
      É o inverso da contribuição de uma evidência incriminadora de mesma força
      (sem o fator de exclusividade, que divide o efeito entre os incriminados):
      log C é simétrico, de modo que uma evidência que afasta o suspeito
      compensa exatamente uma que o incrimina com os mesmos r e v.

    É a única definição da fórmula: o motor bayesiano e a tela de Análise
    Probabilística usam esta função, para que a explicação sempre bata com o
    cálculo.
    """
    if efeito == EFEITO_INOCENTA:
        return 1.0 / (1.0 + reliability * link_weight)
    return 1.0 + (reliability * link_weight * (1.0 / max(n_linked, 1)))


# Limite do argumento de exp() para evitar overflow em float64 (e^709 ≈ 8e307).
MAX_LOG_EXP = 700.0


class BayesianNetwork:
    """
    PRIORA v2 — Log-Bayes com Likelihood Ratio (LR)

    Melhorias:
    - estabilidade numérica (log-space)
    - evidência comparativa (LR)
    - elimina viés de "suspeito vazio"
    """

    def __init__(self, epsilon: float = 1e-6):
        """
        epsilon evita log(0) e define piso mínimo para probabilidades.
        """
        self.epsilon = epsilon

    # ──────────────────────────────────────────────────────────────
    # CORE
    # ──────────────────────────────────────────────────────────────

    def run(
      self,
      case_id: str,
      suspects: List[Suspect],
      evidences: List[Evidence],
      version: int = 2,
      previous_results: Optional[List[SuspectResult]] = None,
    ) -> BayesianAnalysisResult:

        if not suspects:
            raise ValueError("A lista de suspeitos não pode estar vazia.")

        n = len(suspects)
        prior = 1.0 / n

        prev_index = {}
        if previous_results:
            prev_index = {r.suspect.id: r.probability_pct for r in previous_results}

        intermediates = []

        for suspect in suspects:
            linked = [e for e in evidences if suspect.id in e.suspect_ids]

            log_score = self._log_likelihood_ratio(suspect, evidences, suspects)

            intermediates.append((suspect, linked, log_score))

        max_log = max(score for _, _, score in intermediates)

        weights = []
        for suspect, linked, log_score in intermediates:
            weight = math.exp(log_score - max_log) * prior
            weights.append((suspect, linked, log_score, weight))

        denominator = sum(w for _, _, _, w in weights) or 1.0

        results = []

        for suspect, linked, log_score, weight in weights:
            posterior = weight / denominator
            pct = posterior * 100
            uncertainty = 100 - pct

            trend = self._compute_trend(suspect.id, pct, prev_index)

            # exp direto estouraria (OverflowError) com ~1000+ evidências fortes;
            # o posterior já usa log-space, estes valores só são armazenados/exibidos.
            safe_likelihood = math.exp(min(log_score, MAX_LOG_EXP))
            bayes_numerator = safe_likelihood * prior

            results.append(SuspectResult(
                suspect=suspect,
                prior=prior,
                p_e_given_h=safe_likelihood,
                numerator=bayes_numerator,
                p_h_given_e=posterior,
                probability_pct=pct,
                uncertainty_pct=uncertainty,
                trend=trend,
                linked_evidences=linked,
            ))

        results.sort(key=lambda r: r.p_h_given_e, reverse=True)

        for i, r in enumerate(results):
            r.position = i + 1

        top = results[0]
        avg_uncertainty = sum(r.uncertainty_pct for r in results) / n

        return BayesianAnalysisResult(
            case_id=case_id,
            version=version,
            n_suspects=n,
            n_evidences=len(evidences),
            ranking=results,
            case_uncertainty=top.uncertainty_pct,
            avg_uncertainty=avg_uncertainty,
        )
    
    def _evidence_contribution(self, suspect: Suspect, evidence: Evidence, all_suspects: list[Suspect]) -> float:
        """
        Implementa C(Hᵢ, eⱼ) da documentação (seção 16.3): 1 + (r × v × 1/|S|) para evidência que
        incrimina e 1 / (1 + r × v) para a que inocenta.

        Uma evidência não vinculada ao suspeito não entra na formulação do
        documento — portanto não deve afetar seu score (contribuição neutra
        = 1, ou seja, log(1) = 0 na soma em log-space).
        """

        if suspect.id not in evidence.suspect_links:
            return 1.0

        peso_vinculo = evidence.suspect_links[suspect.id]

        # suspeitos que também recebem essa evidência (fator de exclusividade)
        return evidence_contribution(
            evidence.reliability,
            peso_vinculo,
            evidence.n_incriminated,
            evidence.effect_for(suspect.id),
        )

    # ──────────────────────────────────────────────────────────────
    # LIKELIHOOD RATIO MODEL
    # ──────────────────────────────────────────────────────────────

    def _log_likelihood_ratio(self, suspect, evidences, all_suspects):
        """
        IMPORTANTE: `_evidence_contribution` retorna valores em [0.5, 2.0]: de 1 a 2 para
        evidência que incrimina (1 + r·v·fatorExclusividade, com r,v ∈ [0,1]) e de 0,5 a 1 para a
        que inocenta (1 / (1 + r·v)); não em (0,1) como
        uma probabilidade. Usar `_clamp` aqui (que teto em 1 - epsilon)
        achatava toda contribuição > 1 de volta para ~1, anulando o efeito
        de qualquer evidência no score. Só é preciso um piso contra
        log(0) — nunca um teto.
        """
        score = 0.0

        for e in evidences:
            contrib = self._evidence_contribution(suspect, e, all_suspects)
            score += math.log(max(contrib, self.epsilon))

        return score

    def _baseline_probability(self, evidence: Evidence) -> float:
        """
        P(E|¬H)

        IMPORTANTE:
        isso define o quanto a evidência é "comum no mundo".

        Ajuste simples e seguro:
        - evidências fortes são raras no não-crime
        """

        # heurística simples e estável
        return self._clamp(1.0 - evidence.reliability)

    def _clamp(self, x: float) -> float:
        return min(max(x, self.epsilon), 1.0 - self.epsilon)

    # ──────────────────────────────────────────────────────────────
    # TREND (inalterado)
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_trend(
        suspect_id: str,
        current_pct: float,
        prev_index: dict[str, float],
        threshold: float = 0.5,
    ) -> Trend:

        if suspect_id not in prev_index:
            return Trend.STABLE

        delta = current_pct - prev_index[suspect_id]

        if delta > threshold:
            return Trend.UP
        if delta < -threshold:
            return Trend.DOWN
        return Trend.STABLE


def shannon_entropy_bits(probabilities: list[float]) -> float:
    """
    H(P) = -Σ pᵢ·log2(pᵢ), em bits (SHANNON, 1948).

    Mede a incerteza de uma distribuição de probabilidade: H = 0 quando um
    resultado é certo (algum pᵢ = 1); H = log2(n) no caso de distribuição
    uniforme entre n resultados (incerteza máxima). Usada pelo módulo de
    Priorização de Ações para medir o ganho de informação esperado (EIG)
    de uma ação como a redução de entropia que ela proporciona
    (LINDLEY, 1956; JACKSON et al., 2019).
    """
    return -sum(p * math.log2(p) for p in probabilities if p > 0)


# ─── Testes / Demonstração ────────────────────────────────────────────────────

if __name__ == "__main__":

    network = BayesianNetwork()
    SEP = "─" * 76

    # ══════════════════════════════════════════════════════════════════════════
    # TESTE 1 — Caso base: 3 suspeitos SEM evidências → deve dar 33.3% cada
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'═' * 76}")
    print("  TESTE 1 — Caso base: 3 suspeitos sem evidências")
    print(f"{'═' * 76}")

    s_base = [
        Suspect(id="a", name="Alice"),
        Suspect(id="b", name="Bob"),
        Suspect(id="c", name="Carlos"),
    ]
    r_base = network.run("caso-base", s_base, [], version=1)

    for r in r_base.ranking:
        print(f"  {r.suspect.name:<10}  {r.probability_pct:>6.2f}%")
    print(f"  Soma total: {r_base.sum_check():.6f}  (deve ser 1.000000)")

    # ══════════════════════════════════════════════════════════════════════════
    # TESTE 2 — Uma evidência forte vincula só Alice → redistribui
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'═' * 76}")
    print("  TESTE 2 — Evidência forte (0.90) vinculada só a Alice")
    print(f"{'═' * 76}")

    ev_forte = [Evidence(id="e1", name="DNA forte", type=EvidenceType.DNA,
                         status=EvidenceStatus.COLETADA, reliability=1.0,
                         suspect_links={"a": 0.90})]
    r_ev = network.run("caso-ev", s_base, ev_forte, version=1)

    for r in r_ev.ranking:
        ev_names = ", ".join(e.name for e in r.linked_evidences) or "nenhuma"
        print(f"  {r.suspect.name:<10}  {r.probability_pct:>6.2f}%   [{ev_names}]")
    print(f"  Soma total: {r_ev.sum_check():.6f}  (deve ser 1.000000)")

    # ══════════════════════════════════════════════════════════════════════════
    # TESTE 3 — Caso Alpha original (7 suspeitos, 7 evidências)
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'═' * 76}")
    print("  TESTE 3 — Caso Alpha (7 suspeitos, 7 evidências)")
    print(f"{'═' * 76}")

    suspects = [
        Suspect(id="s1", name="Elvin Bond",    age=34),
        Suspect(id="s2", name="Emma Berger",   age=28),
        Suspect(id="s3", name="Koen Chegg",    age=41),
        Suspect(id="s4", name="Kay Finley",    age=25),
        Suspect(id="s5", name="Nicholas Roy",  age=37),
        Suspect(id="s6", name="Louis Mason",   age=30),
        Suspect(id="s7", name="Boston Thomas", age=45),
    ]

    evidences = [
        Evidence(id="e1", name="Digital no local", type=EvidenceType.DIGITAL,    status=EvidenceStatus.COLETADA,   reliability=1.0, suspect_links={"s1": 0.75, "s2": 0.75}),
        Evidence(id="e2", name="DNA amostra #1",   type=EvidenceType.DNA,        status=EvidenceStatus.EM_ANALISE, reliability=1.0, suspect_links={"s1": 0.80, "s3": 0.80}),
        Evidence(id="e3", name="Depoimento teste", type=EvidenceType.DEPOIMENTO, status=EvidenceStatus.CUSTODIADA, reliability=1.0, suspect_links={"s1": 0.32}),
        Evidence(id="e4", name="Digital entrada",  type=EvidenceType.DIGITAL,    status=EvidenceStatus.EM_ANALISE, reliability=1.0, suspect_links={"s2": 0.50, "s4": 0.50}),
        Evidence(id="e5", name="DNA amostra #2",   type=EvidenceType.DNA,        status=EvidenceStatus.CUSTODIADA, reliability=1.0, suspect_links={"s3": 0.60}),
        Evidence(id="e6", name="Depoimento B",     type=EvidenceType.DEPOIMENTO, status=EvidenceStatus.CUSTODIADA, reliability=1.0, suspect_links={"s5": 0.25, "s6": 0.25}),
        Evidence(id="e7", name="DNA amostra #3",   type=EvidenceType.DNA,        status=EvidenceStatus.COLETADA,   reliability=1.0, suspect_links={"s7": 0.15}),
    ]

    previous_mock = [
        SuspectResult(suspect=suspects[0], prior=1/7, p_e_given_h=0, numerator=0, p_h_given_e=0, probability_pct=66.0, uncertainty_pct=34.0),
        SuspectResult(suspect=suspects[1], prior=1/7, p_e_given_h=0, numerator=0, p_h_given_e=0, probability_pct=62.0, uncertainty_pct=38.0),
        SuspectResult(suspect=suspects[2], prior=1/7, p_e_given_h=0, numerator=0, p_h_given_e=0, probability_pct=40.0, uncertainty_pct=60.0),
        SuspectResult(suspect=suspects[3], prior=1/7, p_e_given_h=0, numerator=0, p_h_given_e=0, probability_pct=20.0, uncertainty_pct=80.0),
        SuspectResult(suspect=suspects[4], prior=1/7, p_e_given_h=0, numerator=0, p_h_given_e=0, probability_pct=15.0, uncertainty_pct=85.0),
        SuspectResult(suspect=suspects[5], prior=1/7, p_e_given_h=0, numerator=0, p_h_given_e=0, probability_pct=12.0, uncertainty_pct=88.0),
        SuspectResult(suspect=suspects[6], prior=1/7, p_e_given_h=0, numerator=0, p_h_given_e=0, probability_pct=3.0,  uncertainty_pct=97.0),
    ]

    result = network.run("caso-alpha", suspects, evidences, version=2, previous_results=previous_mock)

    print(f"\n  Suspeitos: {result.n_suspects}  |  Evidências: {result.n_evidences}")
    print(f"  Incerteza do caso : {result.case_uncertainty:.2f}%")
    print(f"  Incerteza média   : {result.avg_uncertainty:.2f}%")
    print(f"  Soma das posteriors: {result.sum_check():.6f}  (deve ser 1.000000)\n")

    print(f"  {'#':<4} {'Nome':<18} {'P(E|H)':>9} {'P(H|E)':>9} {'Prob%':>7} {'Tend.':>7}   Evidências")
    print(f"  {SEP}")

    for r in result.ranking:
        ev_names  = ", ".join(e.name for e in r.linked_evidences) or "nenhuma"
        trend_sym = {"Alta": "↑", "Baixa": "↓", "Estável": "—"}[r.trend.value]
        print(
            f"  {r.position:<4} {r.suspect.name:<18} "
            f"{r.p_e_given_h:>9.4f} {r.p_h_given_e:>9.4f} "
            f"{r.probability_pct:>6.1f}% {trend_sym:>7}   {ev_names}"
        )

    print(f"\n  Fórmula detalhada — {result.ranking[0].suspect.name} (#1):")
    top = result.ranking[0]
    denom = sum(r.numerator for r in result.ranking)
    print(f"    Prior P(H)       = 1/{result.n_suspects} = {top.prior:.6f}")
    print(f"    P(E|H)           = {top.p_e_given_h:.6f}  (produto dos pesos das evidências vinculadas)")
    print(f"    Numerador        = P(E|H) · P(H) = {top.numerator:.6f}")
    print(f"    Denominador      = Σⱼ[P(E|Hⱼ)·P(Hⱼ)] = {denom:.6f}  (soma global)")
    print(f"    P(H|E)           = {top.p_h_given_e:.6f}  ({top.probability_pct:.2f}%)")
    print()
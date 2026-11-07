"""
Evolução da incerteza média dos casos ativos de um usuário.

Cada recálculo bayesiano grava um instantâneo (:AnaliseProb) por suspeito. A
incerteza de um caso, em um instante, é a do suspeito líder (a menor entre os
suspeitos), o mesmo valor guardado em Caso.incerteza e usado no card
"Incerteza média" de Meus Casos.

Para cada instante em que algum caso foi recalculado, calcula-se a média da
incerteza de todos os casos que já tinham análise até aquele momento (cada um
com o seu valor mais recente). Casos sem análise ainda não entram.
"""
from collections import defaultdict


def aggregate_uncertainty_evolution(rows: list[dict], max_points: int = 30) -> list[dict]:
    """
    rows: [{"casoId": str, "calculadoEm": str, "incerteza": float}, ...]
    (uma linha por caso e instante). `calculadoEm` é ISO 8601 e ordena como texto.
    Devolve [{"calculadoEm": str, "incerteza": float, "casos": int}, ...] em
    ordem cronológica, limitado aos `max_points` instantes mais recentes.
    """
    by_case: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        if r.get("incerteza") is None or not r.get("calculadoEm"):
            continue
        by_case[r["casoId"]][r["calculadoEm"]] = float(r["incerteza"])

    timestamps = sorted({t for series in by_case.values() for t in series})

    # último valor conhecido de cada caso, avançando no tempo
    latest: dict[str, float] = {}
    points = []
    for t in timestamps:
        for caso_id, series in by_case.items():
            if t in series:
                latest[caso_id] = series[t]
        if latest:
            points.append({
                "calculadoEm": t,
                "incerteza": round(sum(latest.values()) / len(latest), 2),
                "casos": len(latest),
            })

    return points[-max_points:]

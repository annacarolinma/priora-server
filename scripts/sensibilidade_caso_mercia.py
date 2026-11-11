"""Teste de sensibilidade dos pesos do caso Mércia Nakashima.

Usa o motor bayesiano real (app.bayes.model) com os pesos cadastrados no caso de validação
e mede o quanto o ranking muda quando os pesos variam. Roda offline: não acessa o banco
nem grava nada.

Uso (na raiz do priora_server):
    python scripts/sensibilidade_caso_mercia.py

Cenários:
  1. um peso por vez, ±0,2;
  2. todos os pesos juntos, ao acaso (±0,1 / ±0,2 / ±0,3 e saltos de um nível da escala);
  3. pior caso dirigido: viés contra o líder em todos os pesos, até a ordem se inverter;
  4. retirada de uma evidência por vez.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bayes.model import BayesianNetwork, Evidence, EvidenceStatus, EvidenceType, Suspect  # noqa: E402

# o terminal do Windows pode não usar UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NAMES = {"S1": "Mizael", "S2": "Evandro", "S3": "Altair"}
# (id, nome, peso da evidência r, {suspeito: peso do vínculo v}) — níveis da escala 0,1/0,3/0,5/0,7/0,9
DATA = [
    ("E1", "Término do namoro", 0.5, {"S1": 0.3}),
    ("E2", "E-mail de rejeição", 0.7, {"S1": 0.3}),
    ("E3", "Antecedente de agressão", 0.3, {"S1": 0.3}),
    ("E4", "Alga no sapato", 0.7, {"S1": 0.5}),
    ("E5", "Segunda linha telefônica", 0.7, {"S1": 0.7, "S2": 0.5}),
    ("E6", "Registros perto da casa", 0.3, {"S1": 0.5, "S2": 0.5}),
    ("E7", "Depoimento de Evandro", 0.5, {"S2": 0.7, "S1": 0.5}),
    ("E8", "Fuga para Sergipe", 0.7, {"S2": 0.3}),
    ("E9", "Saída da delegacia", 0.7, {"S1": 0.3}),
    ("E10", "Versões diferentes", 0.3, {"S1": 0.3}),
    ("E11", "27 ligações Mizael–Altair", 0.7, {"S3": 0.1}),
]
LO, HI = 0.05, 0.95  # os pesos ficam estritamente entre 0 e 1
net = BayesianNetwork()
suspects = [Suspect(id=k, name=v) for k, v in NAMES.items()]

PARAMS = []  # (tipo, índice da evidência, suspeito)
for i, (_, _, _, links) in enumerate(DATA):
    PARAMS.append(("r", i, None))
    for s in links:
        PARAMS.append(("v", i, s))


def base_vector():
    return [DATA[i][2] if kind == "r" else DATA[i][3][s] for kind, i, s in PARAMS]


def run(vec, drop=None):
    store = {p: min(HI, max(LO, val)) for p, val in zip(PARAMS, vec)}
    ev = []
    for i, (eid, nome, _, links) in enumerate(DATA):
        if drop == eid:
            continue
        ev.append(Evidence(
            id=eid, name=nome, type=EvidenceType.OUTRA, status=EvidenceStatus.COLETADA,
            reliability=store[("r", i, None)],
            suspect_links={s: store[("v", i, s)] for s in links},
        ))
    ranking = net.run("c", suspects, ev).ranking
    pct = {r.suspect.id: r.probability_pct for r in ranking}
    return pct, tuple(sorted(pct, key=lambda k: -pct[k]))


def fmt(p):
    return " / ".join(f"{NAMES[k]} {p[k]:.1f}%" for k in ("S1", "S2", "S3"))


def ordem(o):
    return " > ".join(NAMES[k] for k in o)


BASE = base_vector()
pct0, ord0 = run(BASE)
print("BASE:", fmt(pct0), "| ordem:", ordem(ord0))

# 1) um parâmetro por vez, ±0,2
print(f"\n[1] UM PESO POR VEZ (±0,2): quantos dos {2 * len(PARAMS)} cenários mudam a ordem?")
mudou = []
for idx, p in enumerate(PARAMS):
    for d in (-0.2, 0.2):
        v = list(BASE)
        v[idx] += d
        pct, order = run(v)
        if order != ord0:
            mudou.append((p, d, order))
print("  mudaram a ordem:", len(mudou), "de", 2 * len(PARAMS))
for p, d, order in mudou:
    print("   -", DATA[p[1]][0], p[0], p[2] or "", f"{d:+.1f}", "->", ordem(order))


# 2) Monte Carlo: todos os pesos variam juntos
def monte_carlo(delta, n=20000, step=None, seed=1):
    rng = random.Random(seed)
    same_order = leader = 0
    series = {k: [] for k in NAMES}
    for _ in range(n):
        if step:  # cada peso muda no máximo um nível da escala
            v = [b + rng.choice((-step, 0, step)) for b in BASE]
        else:
            v = [b + rng.uniform(-delta, delta) for b in BASE]
        pct, order = run(v)
        same_order += order == ord0
        leader += order[0] == ord0[0]
        for k in NAMES:
            series[k].append(pct[k])

    def q(xs, f):
        return sorted(xs)[int(f * (len(xs) - 1))]

    print(f"  mesma ordem completa: {100 * same_order / n:.1f}% | mesmo líder: {100 * leader / n:.1f}%")
    for k in NAMES:
        print(f"   {NAMES[k]:8s} P5={q(series[k], 0.05):5.1f}%  mediana={q(series[k], 0.5):5.1f}%  P95={q(series[k], 0.95):5.1f}%")


print("\n[2] TODOS OS PESOS VARIANDO JUNTOS (20.000 sorteios)")
for d in (0.1, 0.2, 0.3):
    print(f" variação uniforme ±{d}:")
    monte_carlo(d)
print(" cada peso muda no máximo 1 nível da escala (−0,2 / 0 / +0,2):")
monte_carlo(0, step=0.2)

# 3) pior caso dirigido contra o líder
print("\n[3] PIOR CASO DIRIGIDO (enviesa tudo contra o líder e a favor dos demais)")
lider = ord0[0]


def adversarial(d):
    v = list(BASE)
    for idx, (kind, i, s) in enumerate(PARAMS):
        if kind == "v":
            v[idx] += -d if s == lider else d
        else:  # confiabilidade: reduz nas evidências só do líder, aumenta nas dos outros
            v[idx] += -d if set(DATA[i][3]) == {lider} else d
    return run(v)


flip = None
for d in [x / 100 for x in range(0, 60)]:
    pct, order = adversarial(d)
    if order[0] != lider and flip is None:
        flip = d
        print(f"  o líder deixa de ser o primeiro com viés de ±{d:.2f} em todos os pesos:", fmt(pct))
    if d in (0.1, 0.2, 0.3):
        print(f"  viés ±{d:.1f}: {fmt(pct)} | ordem: {ordem(order)}")
if flip is None:
    print("  o líder se mantém mesmo com viés de ±0,59 em todos os pesos")

# 4) retirar uma evidência por vez
print("\n[4] RETIRANDO UMA EVIDÊNCIA POR VEZ (a conclusão depende de alguma delas?)")
for eid, nome, _, _ in DATA:
    pct, order = run(BASE, drop=eid)
    marca = "" if order == ord0 else "   <-- MUDA A ORDEM"
    print(f"  sem {eid:3s} {nome:28s} {fmt(pct)}{marca}")

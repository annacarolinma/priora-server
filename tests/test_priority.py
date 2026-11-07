"""Testes da priorização de ações (RF11): entropia de Shannon e impacto."""
import math

import pytest

from app.bayes.model import shannon_entropy_bits
from app.repositories.priority_repository import _impact_level


def test_entropia_de_certeza_e_zero():
    assert shannon_entropy_bits([1.0, 0.0, 0.0]) == pytest.approx(0.0)


def test_entropia_uniforme_e_log2_n():
    for n in (2, 3, 4, 8):
        assert shannon_entropy_bits([1 / n] * n) == pytest.approx(math.log2(n))


def test_entropia_moeda_viciada():
    # H(0,9; 0,1) = -(0,9 log2 0,9 + 0,1 log2 0,1) ≈ 0,4690
    assert shannon_entropy_bits([0.9, 0.1]) == pytest.approx(0.468996, abs=1e-5)


def test_entropia_nunca_negativa_e_limitada():
    h = shannon_entropy_bits([0.7, 0.2, 0.1])
    assert 0 <= h <= math.log2(3)


def test_ganho_de_informacao_e_reducao_de_entropia():
    antes = shannon_entropy_bits([1 / 3, 1 / 3, 1 / 3])
    depois = shannon_entropy_bits([0.8, 0.1, 0.1])
    assert antes - depois > 0  # a evidência que concentra a probabilidade reduz a incerteza


@pytest.mark.parametrize("pct,nivel", [
    (30, "Alto"), (15, "Alto"), (14.99, "Médio"), (5, "Médio"), (4.99, "Baixo"), (0, "Baixo"),
])
def test_nivel_de_impacto(pct, nivel):
    assert _impact_level(pct) == nivel

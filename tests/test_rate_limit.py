"""Limitador de tentativas de login falhas."""
from app.core import rate_limit
from app.core.rate_limit import FailedAttemptLimiter


def test_bloqueia_depois_de_5_falhas():
    lim = FailedAttemptLimiter(max_attempts=5, window_seconds=900)
    for _ in range(4):
        lim.register_failure("a@b.c")
        assert lim.retry_after("a@b.c") == 0
    lim.register_failure("a@b.c")
    assert lim.retry_after("a@b.c") > 0


def test_chaves_sao_independentes():
    lim = FailedAttemptLimiter(max_attempts=2, window_seconds=900)
    lim.register_failure("a@b.c")
    lim.register_failure("a@b.c")
    assert lim.retry_after("a@b.c") > 0
    assert lim.retry_after("outro@b.c") == 0


def test_login_correto_zera_o_contador():
    lim = FailedAttemptLimiter(max_attempts=3, window_seconds=900)
    lim.register_failure("a@b.c")
    lim.register_failure("a@b.c")
    lim.reset("a@b.c")
    lim.register_failure("a@b.c")
    assert lim.retry_after("a@b.c") == 0


def test_bloqueio_expira_com_a_janela(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: agora[0])
    lim = FailedAttemptLimiter(max_attempts=2, window_seconds=60)
    lim.register_failure("a@b.c")
    lim.register_failure("a@b.c")
    assert lim.retry_after("a@b.c") > 0
    agora[0] += 61
    assert lim.retry_after("a@b.c") == 0

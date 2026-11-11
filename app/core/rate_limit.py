"""
Limitador simples de tentativas de login falhas (em memória).

Bloqueia uma chave (e-mail) depois de MAX_ATTEMPTS falhas dentro da janela
WINDOW_SECONDS. Um login bem-sucedido zera o contador. É suficiente para uma
única instância da API (caso do Docker/rede da delegacia); com várias
instâncias seria preciso um armazenamento compartilhado.
"""

import threading
import time

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60


class FailedAttemptLimiter:
    def __init__(self, max_attempts=MAX_ATTEMPTS, window_seconds=WINDOW_SECONDS):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self.window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def retry_after(self, key: str) -> int:
        """Segundos até poder tentar de novo (0 se não está bloqueado)."""
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            if len(recent) < self.max_attempts:
                return 0
            return max(1, int(self.window - (now - recent[0])))

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._recent(key, now)
            self._failures.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


class Cooldown:
    """Intervalo mínimo entre duas ações da mesma chave (ex.: reenvio de e-mail)."""

    def __init__(self, seconds: int):
        self.seconds = seconds
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def try_acquire(self, key: str) -> int:
        """0 se liberou (e já registra o uso); senão, segundos até poder de novo."""
        now = time.monotonic()
        with self._lock:
            last = self._last.get(key)
            if last is not None and now - last < self.seconds:
                return max(1, int(self.seconds - (now - last)))
            self._last[key] = now
            return 0


login_limiter = FailedAttemptLimiter()
verification_cooldown = Cooldown(60)

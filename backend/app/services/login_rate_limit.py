"""Limiter local simples, limitado em memória; um processo/instância na DEMO.

Usa somente hashes de IP/matrícula e relógio monotônico. Nunca recebe senha.
Não lê X-Forwarded-For: o ASGI server resolve proxies confiáveis.
"""
import hashlib
from threading import Lock
from time import monotonic
from math import ceil


class LoginRateLimiter:
    def __init__(self, clock=monotonic, max_entries=10000):
        self.clock, self.max_entries = clock, max_entries
        self.entries = {}
        self.lock = Lock()

    def _keys(self, ip, matricula):
        return [hashlib.sha256(value.encode()).hexdigest() for value in
                ('ip:' + ip, 'user:' + matricula.strip().casefold())]

    def _prune(self, now, window):
        for key in list(self.entries):
            count, start, blocked_until = self.entries[key]
            if now >= max(start + window, blocked_until):
                del self.entries[key]

    def retry_after(self, ip, matricula, window):
        with self.lock:
            now = self.clock()
            self._prune(now, window)
            keys = self._keys(ip, matricula)
            if len(self.entries) >= self.max_entries and any(k not in self.entries for k in keys):
                return 1  # Falha fechada sob pressão, sem memória ilimitada.
            return max([0] + [max(0, ceil(self.entries[k][2] - now))
                             for k in self._keys(ip, matricula) if k in self.entries])

    def failure(self, ip, matricula, limit, window, block):
        with self.lock:
            now = self.clock()
            self._prune(now, window)
            for key in self._keys(ip, matricula):
                # Limite de memória: não remove bloqueios existentes sob pressão.
                if key not in self.entries and len(self.entries) >= self.max_entries:
                    continue
                count, start, until = self.entries.get(key, (0, now, 0))
                if now >= start + window and now >= until:
                    count, start = 0, now
                count += 1
                self.entries[key] = (count, start, now + block if count >= limit else until)

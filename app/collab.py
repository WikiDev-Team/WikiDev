"""Edição simultânea: presença de quem está na página e mescla de alterações.

A página é feita de blocos salvos um a um, então a colaboração acontece em
três partes, sem precisar de WebSocket nem de um servidor extra:

* **Presença** — cada aba aberta numa página manda um sinal a cada poucos
  segundos dizendo quem está ali e qual bloco está editando. O registro fica
  em memória (some sozinho depois de ``PRESENCE_TTL``), o que basta para um
  processo único do uvicorn, que é como o projeto roda.
* **Sincronização** — a resposta do mesmo sinal traz os blocos que outras
  pessoas criaram, alteraram ou excluíram desde a última consulta, e o htmx
  troca só esses blocos na tela (os que você está editando ficam intactos).
* **Mescla na hora de salvar** — o formulário de edição guarda o conteúdo que
  o bloco tinha quando foi aberto. Se outra pessoa salvou nesse meio-tempo,
  fazemos uma mescla de três vias por linha (como o ``git merge``): mudanças
  em linhas diferentes são combinadas; mudanças nas mesmas linhas viram um
  conflito para a pessoa resolver, sem perder nenhuma das versões.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from difflib import SequenceMatcher

PRESENCE_TTL = 15.0  # segundos sem sinal até a pessoa sair da lista
HEARTBEAT_SECONDS = 4

MINE_LABEL = "Sua versão"
THEIRS_LABEL = "Versão salva por {name}"


# ── Presença ─────────────────────────────────────────────────────────────────


@dataclass
class Presence:
    user_id: int
    username: str
    display_name: str
    editing: frozenset[int]
    seen: float

    @property
    def name(self) -> str:
        return self.display_name or self.username

    @property
    def initials(self) -> str:
        parts = self.name.split()
        letters = "".join(part[0] for part in parts[:2]) if parts else self.username[:1]
        return letters.upper() or "?"


class PresenceRegistry:
    def __init__(self, ttl: float = PRESENCE_TTL, clock=time.monotonic) -> None:
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.Lock()
        self._pages: dict[int, dict[int, Presence]] = {}

    def _prune(self, page_id: int) -> dict[int, Presence]:
        now = self._clock()
        people = self._pages.get(page_id, {})
        for user_id in [uid for uid, item in people.items() if now - item.seen > self._ttl]:
            del people[user_id]
        if not people:
            self._pages.pop(page_id, None)
        return people

    def touch(self, page_id: int, user, editing: set[int] | frozenset[int] = frozenset()) -> None:
        with self._lock:
            people = self._pages.setdefault(page_id, {})
            people[user.id] = Presence(
                user_id=user.id,
                username=user.username,
                display_name=user.display_name or "",
                editing=frozenset(editing),
                seen=self._clock(),
            )

    def start_editing(self, page_id: int, user, block_id: int) -> None:
        with self._lock:
            current = self._prune(page_id).get(user.id)
        editing = set(current.editing) if current else set()
        editing.add(block_id)
        self.touch(page_id, user, editing)

    def others(self, page_id: int, user_id: int) -> list[Presence]:
        with self._lock:
            people = self._prune(page_id)
            return sorted(
                (item for uid, item in people.items() if uid != user_id),
                key=lambda item: item.name.lower(),
            )

    def editing_block(self, page_id: int, block_id: int, user_id: int) -> list[Presence]:
        return [item for item in self.others(page_id, user_id) if block_id in item.editing]

    def clear(self) -> None:
        with self._lock:
            self._pages.clear()


presence = PresenceRegistry()


# ── Mescla de três vias ──────────────────────────────────────────────────────


@dataclass
class MergeResult:
    content: str
    conflicts: int

    @property
    def clean(self) -> bool:
        return self.conflicts == 0


def _sync_regions(base: list[str], mine: list[str], theirs: list[str]):
    """Trechos da base que continuam iguais nas duas versões (estilo diff3)."""
    mine_matches = SequenceMatcher(None, base, mine, autojunk=False).get_matching_blocks()
    theirs_matches = SequenceMatcher(None, base, theirs, autojunk=False).get_matching_blocks()
    regions = []
    i = j = 0
    while i < len(mine_matches) and j < len(theirs_matches):
        m_base, m_pos, m_len = mine_matches[i]
        t_base, t_pos, t_len = theirs_matches[j]
        start = max(m_base, t_base)
        end = min(m_base + m_len, t_base + t_len)
        if start < end:
            regions.append(
                (start, end, m_pos + start - m_base, m_pos + end - m_base,
                 t_pos + start - t_base, t_pos + end - t_base)
            )
        if m_base + m_len < t_base + t_len:
            i += 1
        else:
            j += 1
    regions.append((len(base), len(base), len(mine), len(mine), len(theirs), len(theirs)))
    return regions


def merge3(base: str, mine: str, theirs: str, theirs_name: str = "outra pessoa") -> MergeResult:
    """Combina as alterações de ``mine`` e ``theirs`` feitas sobre ``base``.

    Linhas mudadas só de um lado são aplicadas; quando os dois lados mudam o
    mesmo trecho de jeitos diferentes, o resultado traz os dois com marcadores
    de conflito no formato do git.
    """
    if mine == theirs:
        return MergeResult(mine, 0)
    if theirs == base:
        return MergeResult(mine, 0)
    if mine == base:
        return MergeResult(theirs, 0)

    keeps_newline = mine.endswith("\n") or not mine

    def lines(text: str) -> list[str]:
        return (text if text.endswith("\n") or not text else text + "\n").splitlines(keepends=True)

    b, m, t = lines(base), lines(mine), lines(theirs)
    out: list[str] = []
    conflicts = 0
    zb = zm = zt = 0
    for b_start, b_end, m_start, m_end, t_start, t_end in _sync_regions(b, m, t):
        base_chunk, mine_chunk, theirs_chunk = b[zb:b_start], m[zm:m_start], t[zt:t_start]
        if mine_chunk or theirs_chunk or base_chunk:
            if mine_chunk == theirs_chunk or theirs_chunk == base_chunk:
                out.extend(mine_chunk)
            elif mine_chunk == base_chunk:
                out.extend(theirs_chunk)
            else:
                conflicts += 1
                out.append(f"<<<<<<< {MINE_LABEL}\n")
                out.extend(mine_chunk)
                out.append("=======\n")
                out.extend(theirs_chunk)
                out.append(f">>>>>>> {THEIRS_LABEL.format(name=theirs_name)}\n")
        out.extend(b[b_start:b_end])
        zb, zm, zt = b_end, m_end, t_end

    merged = "".join(out)
    if not keeps_newline and merged.endswith("\n") and not conflicts:
        merged = merged[:-1]
    return MergeResult(merged, conflicts)

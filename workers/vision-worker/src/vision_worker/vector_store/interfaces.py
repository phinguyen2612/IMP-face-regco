from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VectorCandidate:
    person_id: str
    score: float


class VectorStore(Protocol):
    adapter_kind: str

    def search(
        self, collection_id: str, embedding: Sequence[float], top_k: int
    ) -> list[VectorCandidate]: ...

    def add(self, collection_id: str, person_id: str, embedding: Sequence[float]) -> None: ...

    def remove(self, collection_id: str, person_id: str) -> None: ...


class StubVectorStore:
    adapter_kind = "stub"

    def search(
        self, collection_id: str, embedding: Sequence[float], top_k: int
    ) -> list[VectorCandidate]:
        return []

    def add(self, collection_id: str, person_id: str, embedding: Sequence[float]) -> None:
        return None

    def remove(self, collection_id: str, person_id: str) -> None:
        return None

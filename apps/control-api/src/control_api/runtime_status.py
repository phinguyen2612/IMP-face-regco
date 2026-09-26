from threading import Lock
from typing import Protocol

from fr_contracts.runtime_status import RuntimeStatus


class RuntimeStatusStore(Protocol):
    def update(self, status: RuntimeStatus) -> None: ...

    def list(self) -> list[RuntimeStatus]: ...


class InMemoryRuntimeStatusStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], RuntimeStatus] = {}
        self._lock = Lock()

    def update(self, status: RuntimeStatus) -> None:
        with self._lock:
            self._items[(status.worker_id, status.camera_id)] = status

    def list(self) -> list[RuntimeStatus]:
        with self._lock:
            return list(self._items.values())

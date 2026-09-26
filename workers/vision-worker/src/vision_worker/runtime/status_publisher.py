from typing import Protocol

import httpx
from fr_contracts.runtime_status import RuntimeStatus


class RuntimeStatusPublisher(Protocol):
    def publish(self, status: RuntimeStatus) -> None: ...


class HttpRuntimeStatusPublisher:
    """Publishes worker snapshots to the control API's internal runtime boundary."""

    def __init__(
        self,
        endpoint: str,
        timeout_seconds: float = 2.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def publish(self, status: RuntimeStatus) -> None:
        response = self._client.put(
            self._endpoint,
            json=status.model_dump(mode="json"),
        )
        response.raise_for_status()

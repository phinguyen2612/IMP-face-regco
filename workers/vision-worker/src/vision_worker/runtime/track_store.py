from dataclasses import dataclass, field
from time import monotonic

from fr_domain.models import TrackKey
from fr_domain.recognition import RecognitionState, VerificationObservation


@dataclass(slots=True)
class TrackState:
    key: TrackKey
    first_seen_ms: int
    last_seen_ms: int
    recognition_state: RecognitionState = RecognitionState.PENDING
    verified_person_id: str | None = None
    verified_at_ms: int | None = None
    last_recognition_at_ms: int | None = None
    observations: list[VerificationObservation] = field(default_factory=list)


class InMemoryTrackStore:
    def __init__(self, ttl_ms: int = 10000) -> None:
        if ttl_ms <= 0:
            raise ValueError("track state TTL must be positive")
        self._ttl_ms = ttl_ms
        self._states: dict[TrackKey, TrackState] = {}

    def get(self, key: TrackKey) -> TrackState | None:
        return self._states.get(key)

    def put(self, state: TrackState) -> None:
        self._states[state.key] = state

    def get_or_create(self, key: TrackKey, seen_at_ms: int) -> TrackState:
        state = self._states.get(key)
        if state is None:
            state = TrackState(key=key, first_seen_ms=seen_at_ms, last_seen_ms=seen_at_ms)
            self._states[key] = state
        else:
            state.last_seen_ms = seen_at_ms
        return state

    def touch(self, key: TrackKey, seen_at_ms: int) -> TrackState:
        state = self._states[key]
        state.last_seen_ms = seen_at_ms
        return state

    def clear_camera(self, camera_id: str) -> int:
        keys = [key for key in self._states if key.camera_id == camera_id]
        for key in keys:
            del self._states[key]
        return len(keys)

    @property
    def active_count(self) -> int:
        return len(self._states)

    def evict_expired(self, now_ms: int | None = None) -> int:
        current = now_ms if now_ms is not None else int(monotonic() * 1000)
        expired = [
            key
            for key, state in self._states.items()
            if current - state.last_seen_ms > self._ttl_ms
        ]
        for key in expired:
            del self._states[key]
        return len(expired)

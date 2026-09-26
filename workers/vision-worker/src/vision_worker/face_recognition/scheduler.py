from dataclasses import dataclass

from fr_config.models import TimingConfig
from fr_domain.recognition import RecognitionState

from vision_worker.runtime.track_store import TrackState


@dataclass(frozen=True, slots=True)
class RecognitionScheduleDecision:
    run_recognition: bool
    reason: str


class RecognitionScheduler:
    def __init__(self, timing: TimingConfig) -> None:
        self._timing = timing

    def evaluate(self, track: TrackState, now_ms: int) -> RecognitionScheduleDecision:
        verified_at_ms = track.verified_at_ms
        if track.recognition_state is RecognitionState.VERIFIED and verified_at_ms is not None:
            age = now_ms - verified_at_ms
            if age < self._timing.verified_identity_ttl_ms:
                return RecognitionScheduleDecision(False, "verified_identity_cache_hit")
            return RecognitionScheduleDecision(True, "verified_identity_expired")

        if track.recognition_state in {RecognitionState.UNKNOWN, RecognitionState.UNCERTAIN}:
            if track.last_recognition_at_ms is None:
                return RecognitionScheduleDecision(True, "recognition_retry_due")
            retry_age = now_ms - track.last_recognition_at_ms
            if retry_age < self._timing.recognition_retry_ms:
                return RecognitionScheduleDecision(False, "recognition_retry")
            return RecognitionScheduleDecision(True, "recognition_retry_due")

        if (
            track.last_recognition_at_ms is not None
            and now_ms - track.last_recognition_at_ms < self._timing.recognition_interval_ms
        ):
            return RecognitionScheduleDecision(False, "recognition_interval")
        return RecognitionScheduleDecision(True, "recognition_due")

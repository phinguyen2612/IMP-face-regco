from fr_config.models import TimingConfig
from fr_domain.models import TrackKey
from fr_domain.recognition import RecognitionState
from vision_worker.face_recognition.scheduler import RecognitionScheduler
from vision_worker.runtime.track_store import TrackState


def track_state(state: RecognitionState) -> TrackState:
    return TrackState(
        key=TrackKey("cam-01", "session-01", 42),
        first_seen_ms=1000,
        last_seen_ms=2000,
        recognition_state=state,
        verified_at_ms=1500 if state is RecognitionState.VERIFIED else None,
        last_recognition_at_ms=1500,
    )


def test_scheduler_reuses_verified_identity_while_cache_is_valid() -> None:
    scheduler = RecognitionScheduler(TimingConfig(verified_identity_ttl_ms=10000))

    decision = scheduler.evaluate(track_state(RecognitionState.VERIFIED), now_ms=5000)

    assert decision.run_recognition is False
    assert decision.reason == "verified_identity_cache_hit"


def test_scheduler_reruns_after_verified_identity_expires() -> None:
    scheduler = RecognitionScheduler(TimingConfig(verified_identity_ttl_ms=10000))

    decision = scheduler.evaluate(track_state(RecognitionState.VERIFIED), now_ms=12000)

    assert decision.run_recognition is True
    assert decision.reason == "verified_identity_expired"


def test_scheduler_enforces_recognition_interval_for_pending_track() -> None:
    scheduler = RecognitionScheduler(TimingConfig(recognition_interval_ms=500))

    decision = scheduler.evaluate(track_state(RecognitionState.PENDING), now_ms=1800)

    assert decision.run_recognition is False
    assert decision.reason == "recognition_interval"


def test_scheduler_uses_retry_interval_for_unknown_track() -> None:
    scheduler = RecognitionScheduler(
        TimingConfig(recognition_interval_ms=500, recognition_retry_ms=5000)
    )

    before_retry = scheduler.evaluate(track_state(RecognitionState.UNKNOWN), now_ms=6499)
    at_retry = scheduler.evaluate(track_state(RecognitionState.UNKNOWN), now_ms=6500)

    assert before_retry.run_recognition is False
    assert before_retry.reason == "recognition_retry"
    assert at_retry.run_recognition is True
    assert at_retry.reason == "recognition_retry_due"

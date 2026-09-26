from fr_config.models import VerificationConfig
from fr_domain.recognition import (
    CandidateMatch,
    QualityWeightedVerifier,
    RecognitionState,
    VerificationObservation,
)


def observation(
    score: float,
    *,
    frame_id: str,
    timestamp_ms: int = 1000,
    quality: float = 0.9,
    embedding_revision: str = "adaface:1.0",
    index_revision: str = "employees:1",
) -> VerificationObservation:
    return VerificationObservation(
        frame_id=frame_id,
        timestamp_ms=timestamp_ms,
        quality_score=quality,
        candidates=[CandidateMatch(person_id="person-1", similarity=score)],
        embedding_model_revision=embedding_revision,
        vector_index_revision=index_revision,
    )


def test_verifier_never_verifies_from_one_frame() -> None:
    verifier = QualityWeightedVerifier(VerificationConfig(min_good_frames=3, max_frames=5))

    result = verifier.observe(observation(0.95, frame_id="frame-1"))

    assert result.state is RecognitionState.PENDING
    assert result.person_id is None


def test_verifier_accepts_consistent_quality_weighted_observations() -> None:
    verifier = QualityWeightedVerifier(
        VerificationConfig(
            min_good_frames=3,
            max_frames=5,
            similarity_threshold=0.72,
            identity_consistency=0.75,
        )
    )

    verifier.observe(observation(0.78, frame_id="frame-1", quality=0.8))
    verifier.observe(observation(0.81, frame_id="frame-2", quality=0.9))
    result = verifier.observe(observation(0.84, frame_id="frame-3", quality=0.95))

    assert result.state is RecognitionState.VERIFIED
    assert result.person_id == "person-1"
    assert result.score >= 0.80


def test_verifier_marks_unknown_after_enough_low_score_evidence() -> None:
    verifier = QualityWeightedVerifier(
        VerificationConfig(min_good_frames=3, max_frames=3, similarity_threshold=0.72)
    )

    verifier.observe(observation(0.40, frame_id="frame-1"))
    verifier.observe(observation(0.45, frame_id="frame-2"))
    result = verifier.observe(observation(0.50, frame_id="frame-3"))

    assert result.state is RecognitionState.UNKNOWN
    assert result.person_id is None


def test_verifier_does_not_count_the_same_frame_more_than_once() -> None:
    verifier = QualityWeightedVerifier(VerificationConfig(min_good_frames=3, max_frames=3))
    repeated = observation(0.95, frame_id="frame-1")

    verifier.observe(repeated)
    verifier.observe(repeated)
    result = verifier.observe(repeated)

    assert result.state is RecognitionState.PENDING
    assert result.observation_count == 1


def test_verifier_requires_minimum_supporting_frames_for_winner() -> None:
    verifier = QualityWeightedVerifier(
        VerificationConfig(
            min_good_frames=3,
            max_frames=3,
            identity_consistency=0.3,
        )
    )
    empty_one = VerificationObservation(
        frame_id="frame-1",
        timestamp_ms=1000,
        quality_score=0.9,
        candidates=[],
        embedding_model_revision="adaface:1.0",
        vector_index_revision="employees:1",
    )
    empty_two = VerificationObservation(
        frame_id="frame-2",
        timestamp_ms=1100,
        quality_score=0.9,
        candidates=[],
        embedding_model_revision="adaface:1.0",
        vector_index_revision="employees:1",
    )

    verifier.observe(empty_one)
    verifier.observe(empty_two)
    result = verifier.observe(observation(0.95, frame_id="frame-3", timestamp_ms=1200))

    assert result.state is RecognitionState.UNKNOWN
    assert result.person_id is None


def test_verifier_times_out_old_evidence() -> None:
    verifier = QualityWeightedVerifier(
        VerificationConfig(min_good_frames=3, max_frames=5, timeout_ms=1000)
    )
    verifier.observe(observation(0.9, frame_id="frame-1", timestamp_ms=0))
    verifier.observe(observation(0.9, frame_id="frame-2", timestamp_ms=500))

    result = verifier.observe(observation(0.9, frame_id="frame-3", timestamp_ms=1500))

    assert result.state is RecognitionState.UNCERTAIN
    assert result.observation_count == 1


def test_verifier_resets_when_embedding_or_index_revision_changes() -> None:
    verifier = QualityWeightedVerifier(VerificationConfig(min_good_frames=3, max_frames=5))
    verifier.observe(observation(0.9, frame_id="frame-1", timestamp_ms=0))
    verifier.observe(observation(0.9, frame_id="frame-2", timestamp_ms=100))

    result = verifier.observe(
        observation(
            0.9,
            frame_id="frame-3",
            timestamp_ms=200,
            embedding_revision="adaface:2.0",
        )
    )

    assert result.state is RecognitionState.PENDING
    assert result.observation_count == 1


def test_verifier_rejects_reordered_observation_window() -> None:
    verifier = QualityWeightedVerifier(VerificationConfig(min_good_frames=3, max_frames=5))
    verifier.observe(observation(0.9, frame_id="frame-1", timestamp_ms=1000))

    result = verifier.observe(observation(0.9, frame_id="frame-2", timestamp_ms=900))

    assert result.state is RecognitionState.UNCERTAIN
    assert result.observation_count == 1

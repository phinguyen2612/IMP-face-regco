from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class VerificationSettings(Protocol):
    min_good_frames: int
    max_frames: int
    timeout_ms: int
    similarity_threshold: float
    identity_consistency: float
    min_candidate_margin: float


class RecognitionState(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CandidateMatch:
    person_id: str
    similarity: float


@dataclass(frozen=True, slots=True)
class VerificationObservation:
    frame_id: str
    timestamp_ms: int
    quality_score: float
    candidates: list[CandidateMatch]
    embedding_model_revision: str
    vector_index_revision: str


@dataclass(frozen=True, slots=True)
class VerificationDecision:
    state: RecognitionState
    person_id: str | None = None
    score: float = 0.0
    observation_count: int = 0


class QualityWeightedVerifier:
    """Bounded multi-frame verifier; one observation can never verify identity."""

    def __init__(self, settings: VerificationSettings) -> None:
        self._settings = settings
        self._observations: list[VerificationObservation] = []

    def observe(self, observation: VerificationObservation) -> VerificationDecision:
        if observation.quality_score <= 0.0:
            return self._decide()

        if any(item.frame_id == observation.frame_id for item in self._observations):
            return self._decide()

        if self._observations:
            previous = self._observations[-1]
            first = self._observations[0]
            revisions_changed = (
                observation.embedding_model_revision != previous.embedding_model_revision
                or observation.vector_index_revision != previous.vector_index_revision
            )
            reordered = observation.timestamp_ms < previous.timestamp_ms
            timed_out = observation.timestamp_ms - first.timestamp_ms > self._settings.timeout_ms

            if revisions_changed:
                self._observations = [observation]
                return self._decide()
            if reordered or timed_out:
                self._observations = [observation]
                return VerificationDecision(
                    RecognitionState.UNCERTAIN,
                    observation_count=1,
                )

        self._observations.append(observation)
        self._observations = self._observations[-self._settings.max_frames :]
        return self._decide()

    def _decide(self) -> VerificationDecision:
        count = len(self._observations)
        if count < self._settings.min_good_frames:
            return VerificationDecision(RecognitionState.PENDING, observation_count=count)

        top_matches = [item.candidates[0] for item in self._observations if item.candidates]
        if not top_matches:
            return self._terminal_or_pending(0.0)

        winner, winner_count = Counter(match.person_id for match in top_matches).most_common(1)[0]
        consistency = winner_count / count
        winner_observations = [
            (observation, observation.candidates[0])
            for observation in self._observations
            if observation.candidates and observation.candidates[0].person_id == winner
        ]
        total_quality = sum(
            max(observation.quality_score, 0.0) for observation, _ in winner_observations
        )
        weighted_score = (
            sum(
                max(observation.quality_score, 0.0) * match.similarity
                for observation, match in winner_observations
            )
            / total_quality
            if total_quality
            else 0.0
        )
        margin = min(self._candidate_margin(observation) for observation, _ in winner_observations)

        if (
            winner_count >= self._settings.min_good_frames
            and consistency >= self._settings.identity_consistency
            and weighted_score >= self._settings.similarity_threshold
            and margin >= self._settings.min_candidate_margin
        ):
            return VerificationDecision(
                RecognitionState.VERIFIED,
                person_id=winner,
                score=weighted_score,
                observation_count=count,
            )
        return self._terminal_or_pending(weighted_score)

    def _terminal_or_pending(self, score: float) -> VerificationDecision:
        state = (
            RecognitionState.UNKNOWN
            if len(self._observations) >= self._settings.max_frames
            else RecognitionState.PENDING
        )
        return VerificationDecision(state, score=score, observation_count=len(self._observations))

    @staticmethod
    def _candidate_margin(observation: VerificationObservation) -> float:
        if not observation.candidates:
            return 0.0
        if len(observation.candidates) == 1:
            return 1.0
        return observation.candidates[0].similarity - observation.candidates[1].similarity

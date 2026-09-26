"""Face Recognition domain types with no infrastructure dependencies."""

from fr_domain.models import ModelType, TrackKey
from fr_domain.recognition import RecognitionState

__all__ = ["ModelType", "RecognitionState", "TrackKey"]

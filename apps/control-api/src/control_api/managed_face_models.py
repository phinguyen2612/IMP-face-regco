"""Registry-assigned face models for live comparison and reference re-embedding."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from time import monotonic
from typing import Any

import numpy as np
from fr_domain.model_management import DeploymentStatus, ModelType
from PIL import Image
from vision_worker.face_recognition.alignment import FaceAligner, FaceAlignmentError
from vision_worker.face_recognition.images import PersonCrop
from vision_worker.inference.adaface_onnx import AdaFaceOnnxEmbedder
from vision_worker.inference.onnx_session import OnnxInferenceSession
from vision_worker.inference.retinaface_onnx import RetinaFaceOnnxDetector
from vision_worker.inference.scrfd_onnx import ScrfdOnnxDetector
from vision_worker.video.frame import VideoFrame

from control_api.model_registry import ModelRegistryService
from control_api.simple_face_recognition import ComparisonError, FaceSample, _point_in_polygon


class ManagedFaceModels:
    def __init__(self, registry: ModelRegistryService) -> None:
        self.registry = registry
        self.detector: RetinaFaceOnnxDetector | ScrfdOnnxDetector | None = None
        self.embedder: AdaFaceOnnxEmbedder | None = None
        self.compatibility_key = ""
        self.profile = "registry-face-models-v1"
        self.model_names: list[str] = []
        self.error: str | None = None
        self._aligner = FaceAligner()
        self.last_latency_ms: float | None = None

    def status(self) -> dict[str, object]:
        return {
            "state": self.error or ("READY" if self.detector else "MODEL_LOADING"),
            "model_names": self.model_names,
            "profile": self.profile,
            "model_revision": self.compatibility_key,
            "runtime": {
                "backend": "onnx_cpu",
                "execution_provider": "CPUExecutionProvider",
                "latest_analysis_ms": self.last_latency_ms,
            },
        }

    def _session(self, version: Any) -> OnnxInferenceSession:
        root = Path("data/model-cache")
        root.mkdir(parents=True, exist_ok=True)
        target = root / f"{version.checksum}.onnx"
        if not target.is_file() or sha256(target.read_bytes()).hexdigest() != version.checksum:
            payload = b"".join(self.registry.artifact_content(version.artifact_id))
            if (
                len(payload) != version.size_bytes
                or sha256(payload).hexdigest() != version.checksum
            ):
                raise ComparisonError("MODEL_CHECKSUM_MISMATCH")
            temporary = target.with_suffix(".api.part")
            try:
                temporary.write_bytes(payload)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return OnnxInferenceSession(target, version.checksum, version.manifest)

    def load(self) -> None:
        detector = None
        embedder = None
        sessions = []
        try:
            assignments = self.registry.repository.list_assignments()
            versions = []
            for role in (ModelType.FACE_DETECTOR, ModelType.FACE_EMBEDDER):
                deployment_id = assignments.get(role)
                if not deployment_id:
                    raise ComparisonError("FACE_MODELS_NOT_ASSIGNED")
                deployment = self.registry.get_deployment(deployment_id)
                if deployment.status is not DeploymentStatus.ACTIVE:
                    raise ComparisonError("FACE_MODEL_NOT_ACTIVE")
                version = self.registry.get_version(deployment.model_version_id)
                if version.manifest.model_type is not role:
                    raise ComparisonError("MODEL_TYPE_MISMATCH")
                versions.append(version)
            key = "/".join(v.id + ":" + v.checksum for v in versions)
            if key == self.compatibility_key and self.detector is not None:
                self.error = None
                return
            for version in versions:
                sessions.append(self._session(version))
            detector_class = (
                RetinaFaceOnnxDetector
                if versions[0].manifest.metadata.get("architecture") == "RETINAFACE"
                else ScrfdOnnxDetector
            )
            detector = detector_class(sessions[0], versions[0].manifest)
            embedder = AdaFaceOnnxEmbedder(sessions[1], versions[1].manifest)
            detector.warmup()
            embedder.warmup()
            old_detector, old_embedder = self.detector, self.embedder
            self.detector, self.embedder = detector, embedder
            self.compatibility_key = key
            self.model_names = [
                "RetinaFace MobileNet 0.25"
                if detector_class is RetinaFaceOnnxDetector
                else "SCRFD",
                "AdaFace",
            ]
            for previous in (old_detector, old_embedder):
                if previous is not None:
                    previous.close()
            self.error = None
        except Exception as error:
            for session in sessions:
                session.close()
            self.error = (
                str(error) if isinstance(error, ComparisonError) else "FACE_MODEL_LOAD_FAILED"
            )
            raise ComparisonError(self.error) from error

    def analyze(
        self, payload: bytes, roi_polygon: list[tuple[float, float]] | None = None
    ) -> list[FaceSample]:
        # RegisteredFaceComparison pins the pair at the start of its locked refresh.
        # Do not switch spaces halfway through rebuilding a gallery or comparing it.
        if self.detector is None or self.embedder is None:
            self.load()
        assert self.detector is not None and self.embedder is not None
        started = monotonic()
        try:
            with Image.open(BytesIO(payload)) as source:
                if source.width * source.height > 20_000_000:
                    raise ComparisonError("IMAGE_TOO_LARGE")
                # Preserve source detail; detector owns its resize and coordinate mapping.
                pixels = np.asarray(source.convert("RGB"))
            h, w = pixels.shape[:2]
            frame = VideoFrame("comparison", "transient", 0, width=w, height=h, pixel_format="RGB")
            crop = PersonCrop(pixels, frame, 0, 0)
            samples = []
            for face in self.detector.detect([crop])[0][:8]:
                box = face.box
                if min(box.x2 - box.x1, box.y2 - box.y1) < 30:
                    continue
                if roi_polygon and not _point_in_polygon(
                    (box.x1 + box.x2) / (2 * w), (box.y1 + box.y2) / (2 * h), roi_polygon
                ):
                    continue
                try:
                    aligned = self._aligner.align(crop, face.landmarks)
                except FaceAlignmentError:
                    # Invalid landmark geometry is an unusable sample, never an identity.
                    continue
                feature = np.asarray(self.embedder.embed([aligned])[0], dtype=np.float32)
                samples.append(
                    FaceSample(
                        [box.x1 / w, box.y1 / h, (box.x2 - box.x1) / w, (box.y2 - box.y1) / h],
                        feature,
                    )
                )
            self.last_latency_ms = (monotonic() - started) * 1000
            return samples
        except ComparisonError:
            raise
        except Exception as error:
            raise ComparisonError("FACE_INFERENCE_FAILED") from error

    def close(self) -> None:
        for model in (self.detector, self.embedder):
            if model is not None:
                model.close()

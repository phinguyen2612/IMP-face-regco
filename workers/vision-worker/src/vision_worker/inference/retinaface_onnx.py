"""RetinaFace MobileNet 0.25 raw loc/conf/landmark ONNX profile."""

from collections.abc import Sequence
from importlib import import_module
from math import ceil
from threading import local
from time import perf_counter
from typing import Any, Literal

from fr_domain.model_management import ModelManifest, ModelType

from vision_worker.face_recognition.images import PersonCrop
from vision_worker.inference.interfaces import (
    BoundingBox,
    FaceDetection,
    FaceLandmarks,
    ModelStageTimings,
)
from vision_worker.inference.onnx_session import OnnxInferenceSession
from vision_worker.inference.scrfd_onnx import _overlap


class RetinaFaceContractError(RuntimeError):
    pass


class RetinaFaceOnnxDetector:
    adapter_kind = "retinaface_onnx"

    def __init__(self, session: OnnxInferenceSession, manifest: ModelManifest) -> None:
        meta, pre = manifest.metadata, manifest.preprocessing
        if manifest.model_type is not ModelType.FACE_DETECTOR:
            raise RetinaFaceContractError("MODEL_TYPE_MISMATCH")
        if (
            meta.get("architecture") != "RETINAFACE"
            or meta.get("backbone") != "mobilenet0.25"
            or meta.get("output_semantics") != "retinaface_loc_conf_landmarks"
            or meta.get("landmark_points") != 5
            or meta.get("min_sizes") != [[16, 32], [64, 128], [256, 512]]
            or meta.get("steps") != [8, 16, 32]
            or meta.get("variance") != [0.1, 0.2]
        ):
            raise RetinaFaceContractError("UNSUPPORTED_RETINAFACE_PROFILE")
        if (
            pre.layout != "NCHW"
            or pre.color_order != "BGR"
            or pre.normalization != "retinaface_bgr_mean_104_117_123"
            or pre.resize_mode != "letterbox"
            or len(manifest.inputs) != 1
            or len(manifest.outputs) != 3
        ):
            raise RetinaFaceContractError("UNSUPPORTED_PREPROCESSING")
        spec = manifest.inputs[0]
        if spec.dtype != "float32" or len(spec.shape) != 4 or spec.shape[:2] != [1, 3]:
            raise RetinaFaceContractError("UNSUPPORTED_INPUT_SHAPE")
        h, w = spec.shape[2:]
        if (
            not isinstance(h, int)
            or not isinstance(w, int)
            or not 32 <= min(h, w) <= max(h, w) <= 1920
        ):
            raise RetinaFaceContractError("UNSUPPORTED_INPUT_SHAPE")
        self._height, self._width = h, w
        self._np = import_module("numpy")
        self._image = import_module("PIL.Image")
        priors = []
        for step, sizes in zip(meta["steps"], meta["min_sizes"], strict=True):
            for y in range(ceil(h / step)):
                for x in range(ceil(w / step)):
                    for size in sizes:
                        priors.append(
                            ((x + 0.5) * step / w, (y + 0.5) * step / h, size / w, size / h)
                        )
        self._priors = self._np.asarray(priors, dtype=self._np.float32)
        for output, columns in zip(manifest.outputs, (4, 2, 10), strict=True):
            if output.dtype != "float32" or output.shape != [1, len(priors), columns]:
                raise RetinaFaceContractError("INVALID_TENSOR_CONTRACT")
        self._confidence = self._threshold(meta.get("confidence_threshold", 0.6))
        self._nms = self._threshold(meta.get("iou_threshold", 0.4))
        self._session = session
        self._thread_timings = local()

    @staticmethod
    def _threshold(value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise RetinaFaceContractError("INVALID_THRESHOLD")
        return float(value)

    def preprocess(self, crop: PersonCrop) -> tuple[Any, tuple[float, float]]:
        np = self._np
        pixels = np.asarray(crop.pixels)
        if (
            pixels.ndim != 3
            or pixels.shape[2] != 3
            or pixels.dtype != np.uint8
            or min(pixels.shape[:2]) <= 0
        ):
            raise RetinaFaceContractError("INVALID_PERSON_ROI")
        scale = min(self._width / crop.width, self._height / crop.height)
        w, h = max(1, round(crop.width * scale)), max(1, round(crop.height * scale))
        resized = np.asarray(
            self._image.fromarray(pixels).resize((w, h), self._image.Resampling.BILINEAR)
        )
        # Padding equals the BGR training mean, becoming zero after normalization.
        canvas = np.empty((self._height, self._width, 3), dtype=np.float32)
        canvas[:] = (104, 117, 123)
        canvas[:h, :w] = resized[:, :, ::-1]
        tensor = np.ascontiguousarray(
            (canvas - (104, 117, 123)).astype(np.float32).transpose(2, 0, 1)[None]
        )
        return tensor, (w / crop.width, h / crop.height)

    def postprocess(
        self, outputs: Sequence[Any], width: int, height: int, scales: tuple[float, float]
    ) -> list[FaceDetection]:
        np = self._np
        if (
            len(outputs) != 3
            or width <= 0
            or height <= 0
            or not all(0 < s < float("inf") for s in scales)
        ):
            raise RetinaFaceContractError("INVALID_MODEL_OUTPUT")
        arrays = [np.asarray(a) for a in outputs]
        for array, columns in zip(arrays, (4, 2, 10), strict=True):
            if (
                array.shape != (1, len(self._priors), columns)
                or array.dtype != np.float32
                or not np.isfinite(array).all()
            ):
                raise RetinaFaceContractError("INVALID_MODEL_OUTPUT")
        loc, conf, landmarks = (a[0] for a in arrays)
        if np.any(conf < 0) or np.any(conf > 1) or not np.allclose(conf.sum(axis=1), 1, atol=1e-4):
            raise RetinaFaceContractError("INVALID_MODEL_OUTPUT")
        selected = np.flatnonzero(conf[:, 1] >= self._confidence)
        selected = selected[np.argsort(-conf[selected, 1], kind="stable")[:300]]
        sx, sy = scales
        candidates = []
        for index in selected:
            prior = self._priors[index]
            if prior[0] * self._width >= width * sx or prior[1] * self._height >= height * sy:
                continue
            # Reject pathological offsets instead of overflowing exp into invalid boxes.
            if np.any(np.abs(loc[index, 2:] * 0.2) > 20):
                raise RetinaFaceContractError("INVALID_MODEL_OUTPUT")
            center = prior[:2] + loc[index, :2] * 0.1 * prior[2:]
            size = prior[2:] * np.exp(loc[index, 2:] * 0.2)
            box = np.concatenate((center - size / 2, center + size / 2))
            box *= np.asarray((self._width / sx, self._height / sy) * 2)
            box = np.clip(box, 0, (width, height, width, height))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            points = prior[:2] + landmarks[index].reshape(5, 2) * 0.1 * prior[2:]
            points *= np.asarray((self._width / sx, self._height / sy))
            candidates.append(
                FaceDetection(
                    BoundingBox(
                        float(box[0]),
                        float(box[1]),
                        float(box[2]),
                        float(box[3]),
                        float(conf[index, 1]),
                    ),
                    FaceLandmarks(*((float(point[0]), float(point[1])) for point in points)),
                )
            )
        kept: list[FaceDetection] = []
        for face in candidates:
            if all(_overlap(face.box, other.box) <= self._nms for other in kept):
                kept.append(face)
        return kept

    def detect(self, person_crops: Sequence[Any]) -> list[list[FaceDetection]]:
        results = []
        for crop in person_crops:
            pre_ms = infer_ms = post_ms = None
            stage: Literal["preprocessing", "inference", "postprocessing"] = "preprocessing"
            failed = None
            started = perf_counter()
            try:
                if not isinstance(crop, PersonCrop):
                    raise RetinaFaceContractError("INVALID_PERSON_ROI")
                tensor, scales = self.preprocess(crop)
                pre_ms = (perf_counter() - started) * 1000
                stage = "inference"
                started = perf_counter()
                outputs = self._session.run({self._session.input_names[0]: tensor})
                infer_ms = (perf_counter() - started) * 1000
                stage = "postprocessing"
                started = perf_counter()
                results.append(self.postprocess(outputs, crop.width, crop.height, scales))
                post_ms = (perf_counter() - started) * 1000
            except Exception:
                failed = stage
                raise
            finally:
                self._thread_timings.value = ModelStageTimings(pre_ms, infer_ms, post_ms, failed)
        return results

    def warmup(self) -> None:
        self.postprocess(self._session.warmup(), self._width, self._height, (1.0, 1.0))

    def timings(self) -> ModelStageTimings:
        return getattr(self._thread_timings, "value", ModelStageTimings())

    @property
    def warmed_up(self) -> bool:
        return self._session.warmup_ms is not None

    @property
    def execution_provider(self) -> str:
        return self._session.provider

    def close(self) -> None:
        self._session.close()

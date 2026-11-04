from __future__ import annotations

import os
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

from fr_domain.model_management import ModelManifest, TensorSpec


class OnnxSessionError(RuntimeError):
    """An ONNX model could not execute under its declared contract."""


def _matches(actual: Any, expected: TensorSpec) -> bool:
    dtype = {
        "float32": "tensor(float)",
        "float16": "tensor(float16)",
        "uint8": "tensor(uint8)",
        "int64": "tensor(int64)",
    }[expected.dtype]
    if actual.name != expected.name or actual.type != dtype:
        return False
    if len(actual.shape) != len(expected.shape):
        return False
    return all(
        declared == observed if isinstance(declared, int) else not isinstance(observed, int)
        for declared, observed in zip(expected.shape, actual.shape, strict=True)
    )


class OnnxInferenceSession:
    def __init__(
        self,
        path: Path,
        checksum: str,
        manifest: ModelManifest,
        provider: str = "CPUExecutionProvider",
    ) -> None:
        self._lock = Lock()
        self._closed = False
        self.last_inference_ms: float | None = None
        self.warmup_ms: float | None = None
        started = perf_counter()
        try:
            artifact = path.read_bytes()
        except OSError as error:
            raise OnnxSessionError("ARTIFACT_MISSING") from error
        if sha256(artifact).hexdigest() != checksum:
            raise OnnxSessionError("CHECKSUM_MISMATCH")
        if provider not in {"CPUExecutionProvider", "CUDAExecutionProvider"}:
            raise OnnxSessionError("PROVIDER_UNSUPPORTED")
        try:
            ort = import_module("onnxruntime")
            self._numpy = import_module("numpy")
        except ImportError as error:
            raise OnnxSessionError("RUNTIME_UNAVAILABLE") from error
        if provider not in ort.get_available_providers():
            raise OnnxSessionError("PROVIDER_UNAVAILABLE")
        options = ort.SessionOptions()
        try:
            threads = int(os.getenv("FR_ORT_INTRA_OP_THREADS", "0"))
            spinning = os.getenv("FR_ORT_ALLOW_SPINNING", "1")
            if not 0 <= threads <= 64 or spinning not in {"0", "1"}:
                raise ValueError
        except ValueError as error:
            raise OnnxSessionError("INVALID_CPU_THREAD_CONFIGURATION") from error
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry("session.intra_op.allow_spinning", spinning)
        options.add_session_config_entry("session.inter_op.allow_spinning", spinning)
        self.intra_op_threads = threads
        self.allow_spinning = spinning == "1"
        try:
            self._session = ort.InferenceSession(
                artifact, sess_options=options, providers=[provider]
            )
        except Exception as error:
            raise OnnxSessionError("MODEL_LOAD_FAILED") from error
        # ONNX Runtime can otherwise silently fall back to CPU after provider failure.
        self._session.disable_fallback()
        if self._session.get_providers()[0] != provider:
            self.close()
            raise OnnxSessionError("PROVIDER_INITIALIZATION_FAILED")
        inputs = self._session.get_inputs()
        outputs = self._session.get_outputs()
        if len(inputs) != len(manifest.inputs) or len(outputs) != len(manifest.outputs):
            self.close()
            raise OnnxSessionError("INVALID_TENSOR_CONTRACT")
        if not all(
            _matches(node, spec) for node, spec in zip(inputs, manifest.inputs, strict=True)
        ):
            self.close()
            raise OnnxSessionError("INVALID_TENSOR_CONTRACT")
        if not all(
            _matches(node, spec) for node, spec in zip(outputs, manifest.outputs, strict=True)
        ):
            self.close()
            raise OnnxSessionError("INVALID_TENSOR_CONTRACT")
        self.input_names = tuple(node.name for node in inputs)
        self.output_names = tuple(node.name for node in outputs)
        self.provider = provider
        self.cold_start_ms = (perf_counter() - started) * 1000
        self._manifest = manifest

    def warmup(self) -> list[Any]:
        tensors: dict[str, Any] = {}
        for spec in self._manifest.inputs:
            shape = tuple(
                value if isinstance(value, int) and value > 0 else 1 for value in spec.shape
            )
            tensors[spec.name] = self._numpy.zeros(shape, dtype=spec.dtype)
        started = perf_counter()
        outputs = self.run(tensors)
        self.warmup_ms = (perf_counter() - started) * 1000
        return outputs

    def run(self, tensors: dict[str, Any]) -> list[Any]:
        if self._closed:
            raise OnnxSessionError("MODEL_CLOSED")
        if set(tensors) != set(self.input_names):
            raise OnnxSessionError("INVALID_TENSOR_CONTRACT")
        started = perf_counter()
        try:
            with self._lock:
                outputs: list[Any] = self._session.run(list(self.output_names), tensors)
        except Exception as error:
            raise OnnxSessionError("INFERENCE_FAILED") from error
        self.last_inference_ms = (perf_counter() - started) * 1000
        return outputs

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._session = None

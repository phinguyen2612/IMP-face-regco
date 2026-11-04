"""Measure local CPU adapters; save timings, never images or identity data."""

import argparse
import gc
import json
import os
import platform
from hashlib import sha256
from pathlib import Path
from time import perf_counter, process_time

import cv2
import numpy as np
import onnxruntime as ort
from control_api.simple_face_recognition import OpenCvFaceModels
from fr_domain.model_management import ModelManifest
from PIL import Image
from vision_worker.inference.onnx_session import OnnxInferenceSession
from vision_worker.inference.yolo_onnx import YoloOnnxDetector
from vision_worker.video.frame import VideoFrame


def measure(call, iterations):
    for _ in range(3):
        call()
    wall, cpu = [], []
    for _ in range(iterations):
        start, cpu_start = perf_counter(), process_time()
        call()
        wall.append((perf_counter() - start) * 1000)
        cpu.append((process_time() - cpu_start) * 1000)
    return {
        "iterations": iterations,
        "median_ms": round(float(np.median(wall)), 3),
        "p95_ms": round(float(np.percentile(wall, 95)), 3),
        "mean_cpu_ms": round(float(np.mean(cpu)), 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--face-image", type=Path)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument(
        "--output", type=Path, default=Path(".runtime/local-inference-benchmark.json")
    )
    args = parser.parse_args()
    if args.iterations < 10:
        parser.error("Use at least 10 measured iterations")
    face_image = args.face_image or next(iter(sorted(Path("data/face-images").glob("*.jpg"))), None)
    report = {
        "schema_version": 1,
        "scope": "recorded-input adapter benchmark; not live camera FPS or accuracy",
        "python": platform.python_version(),
        "platform": platform.system(),
        "opencv": cv2.__version__,
        "onnxruntime": ort.__version__,
        "providers": ort.get_available_providers(),
        "warmup_iterations": 3,
        "face_artifacts_sha256": {
            role: spec["sha256"]
            for role, spec in OpenCvFaceModels().config.items()
            if role in {"detector", "recognizer"}
        },
        "face": [],
        "person": [],
    }
    if face_image is not None:
        payload = face_image.read_bytes()
        reference = None
        for threads in [cv2.getNumThreads(), 1, 2, 4, 6]:
            os.environ["FR_OPENCV_THREADS"] = str(threads)
            models = OpenCvFaceModels()
            models.load()
            faces = models.analyze(payload)
            if not faces:
                raise RuntimeError("Benchmark needs an image containing a detectable face")
            if reference is None:
                reference = faces
            equivalent = len(faces) == len(reference) and all(
                np.allclose(a.box, b.box, atol=1e-5)
                and np.allclose(a.feature, b.feature, atol=1e-5)
                for a, b in zip(faces, reference, strict=True)
            )
            result = {
                "threads": threads,
                "output_equivalent_atol_1e-5": equivalent,
                **measure(lambda models=models: models.analyze(payload), args.iterations),
            }
            report["face"].append(result)
            print("face", json.dumps(result), flush=True)
            del models
            gc.collect()
    artifact = Path("data/models/yolo26/yolo26n.onnx")
    manifest_path = artifact.parent / "manifest.json"
    image_path = artifact.parent / "bus.jpg"
    if artifact.is_file() and manifest_path.is_file() and image_path.is_file():
        manifest = ModelManifest.model_validate_json(manifest_path.read_bytes())
        checksum = sha256(artifact.read_bytes()).hexdigest()
        report["person_artifact_sha256"] = checksum
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            frame = VideoFrame(
                "benchmark", "recorded", 1, 0, rgb.width, rgb.height, "RGB", rgb.tobytes()
            )
        reference = None
        for threads, spinning in [(0, "1"), (1, "0"), (2, "0"), (4, "0"), (6, "0")]:
            os.environ["FR_ORT_INTRA_OP_THREADS"] = str(threads)
            os.environ["FR_ORT_ALLOW_SPINNING"] = spinning
            session = OnnxInferenceSession(artifact, checksum, manifest)
            detector = YoloOnnxDetector(session, manifest)
            detector.warmup()
            boxes = detector.detect([frame])
            if reference is None:
                reference = boxes
            equivalent = len(boxes[0]) == len(reference[0]) and all(
                np.allclose(
                    [a.x1, a.y1, a.x2, a.y2, a.confidence],
                    [b.x1, b.y1, b.x2, b.y2, b.confidence],
                    atol=1e-4,
                )
                for a, b in zip(boxes[0], reference[0], strict=True)
            )
            result = {
                "threads": threads,
                "spinning": spinning,
                "output_equivalent_atol_1e-4": equivalent,
                **measure(lambda detector=detector: detector.detect([frame]), args.iterations),
            }
            report["person"].append(result)
            print("person", json.dumps(result), flush=True)
            detector.close()
            del detector, session
            gc.collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

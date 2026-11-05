"""Controlled tensors test RetinaFace semantics, not accuracy on CCTV."""

import numpy as np
import pytest
from fr_domain.model_management import ModelManifest
from vision_worker.face_recognition.images import PersonCrop
from vision_worker.inference.retinaface_onnx import RetinaFaceContractError, RetinaFaceOnnxDetector
from vision_worker.video.frame import VideoFrame


def manifest():
    return ModelManifest.model_validate(
        {
            "model_type": "FACE_DETECTOR",
            "inputs": [{"name": "input", "shape": [1, 3, 32, 32], "dtype": "float32"}],
            "outputs": [
                {"name": name, "shape": [1, 42, cols], "dtype": "float32"}
                for name, cols in [("loc", 4), ("conf", 2), ("landmarks", 10)]
            ],
            "preprocessing": {
                "layout": "NCHW",
                "color_order": "BGR",
                "normalization": "retinaface_bgr_mean_104_117_123",
                "resize_mode": "letterbox",
            },
            "metadata": {
                "architecture": "RETINAFACE",
                "backbone": "mobilenet0.25",
                "output_semantics": "retinaface_loc_conf_landmarks",
                "landmark_points": 5,
                "min_sizes": [[16, 32], [64, 128], [256, 512]],
                "steps": [8, 16, 32],
                "variance": [0.1, 0.2],
            },
        }
    )


def outputs():
    loc = np.zeros((1, 42, 4), np.float32)
    conf = np.zeros((1, 42, 2), np.float32)
    conf[:, :, 0] = 1
    land = np.zeros((1, 42, 10), np.float32)
    return [loc, conf, land]


def test_prior_decode_restores_original_coordinates_and_landmarks():
    detector = RetinaFaceOnnxDetector(None, manifest())
    values = outputs()
    values[1][0, 0] = [0.05, 0.95]
    faces = detector.postprocess(values, 64, 64, (0.5, 0.5))
    assert len(faces) == 1
    assert (faces[0].box.x1, faces[0].box.y1, faces[0].box.x2, faces[0].box.y2) == (0, 0, 24, 24)
    assert faces[0].landmarks.nose == (8, 8)


def test_letterbox_padding_anchors_are_excluded():
    detector = RetinaFaceOnnxDetector(None, manifest())
    values = outputs()
    values[1][0, 24] = [0.01, 0.99]  # y=28 belongs to padding below a 32x16 image
    assert detector.postprocess(values, 32, 16, (1, 1)) == []


@pytest.mark.parametrize("corruption", ["nan", "shape", "scores", "overflow"])
def test_malformed_outputs_are_errors_instead_of_no_face(corruption):
    detector = RetinaFaceOnnxDetector(None, manifest())
    values = outputs()
    if corruption == "nan":
        values[0][0, 0, 0] = np.nan
    elif corruption == "shape":
        values[2] = values[2][:, :-1]
    elif corruption == "scores":
        values[1][0, 0] = [0.8, 0.8]
    else:
        values[1][0, 0] = [0.01, 0.99]
        values[0][0, 0, 2] = 1000
    with pytest.raises(RetinaFaceContractError, match="INVALID_MODEL_OUTPUT"):
        detector.postprocess(values, 32, 32, (1, 1))


def test_preprocessing_uses_bgr_training_mean_and_zero_padding():
    detector = RetinaFaceOnnxDetector(None, manifest())
    pixels = np.empty((16, 32, 3), np.uint8)
    pixels[:] = (123, 117, 104)
    tensor, scales = detector.preprocess(PersonCrop(pixels, VideoFrame("cam", "session", 1), 0, 0))
    assert tensor.dtype == np.float32
    assert tensor.shape == (1, 3, 32, 32)
    assert np.max(np.abs(tensor)) == 0
    assert scales == (1, 1)


def test_all_background_is_a_successful_empty_detection():
    detector = RetinaFaceOnnxDetector(None, manifest())
    assert detector.postprocess(outputs(), 32, 32, (1, 1)) == []

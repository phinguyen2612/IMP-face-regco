"""Export upstream RetinaFace MobileNet and CVLFace AdaFace IR18 to fixed ONNX.

PyTorch, torchvision and safetensors are provisioning dependencies only.
Source checkouts and model weights stay outside version control.
"""

import argparse
import importlib.util
import json
import sys
from hashlib import sha256
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retinaface-source", required=True, type=Path)
    parser.add_argument("--adaface-source", required=True, type=Path)
    parser.add_argument("--retinaface-weights", required=True, type=Path)
    parser.add_argument("--adaface-weights", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/models/retinaface-adaface"))
    args = parser.parse_args()
    import numpy as np
    import onnxruntime as ort
    import torch
    from safetensors.torch import load_file

    torch.set_num_threads(2)
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.retinaface_source.resolve()))
    from models.retinaface import RetinaFace

    from data import cfg_mnet

    detector = RetinaFace(dict(cfg_mnet, pretrain=False), phase="test").eval()
    state = torch.load(args.retinaface_weights, map_location="cpu", weights_only=True)
    detector.load_state_dict({k.removeprefix("module."): v for k, v in state.items()}, strict=True)
    spec = importlib.util.spec_from_file_location(
        "upstream_adaface_net", args.adaface_source / "net.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    backbone = module.build_model("ir_18").eval()
    weights = load_file(str(args.adaface_weights))
    if not all(k.startswith("model.net.") for k in weights):
        raise ValueError("UNEXPECTED_CVLFACE_WEIGHTS")
    backbone.load_state_dict(
        {k.removeprefix("model.net."): v for k, v in weights.items()}, strict=True
    )

    class Embedder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = backbone

        def forward(self, pixels):
            # CVLFace weights consume RGB; raw pre-normalization embedding.
            normalized, norm = self.backbone(pixels)
            return normalized * norm

    models = [
        ("retinaface-mobilenet025", detector, (1, 3, 640, 640), ["loc", "conf", "landmarks"]),
        ("adaface-ir18-webface4m", Embedder().eval(), (1, 3, 112, 112), ["embedding"]),
    ]
    for name, model, shape, output_names in models:
        target = args.output / (name + ".onnx")
        tensor = torch.randn(shape)
        with torch.no_grad():
            reference = model(tensor)
            torch.onnx.export(
                model,
                tensor,
                str(target),
                input_names=["input"],
                output_names=output_names,
                opset_version=17,
                dynamo=False,
            )
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        session = ort.InferenceSession(
            str(target), sess_options=options, providers=["CPUExecutionProvider"]
        )
        outputs = session.run(None, {"input": tensor.numpy()})
        expected = list(reference) if isinstance(reference, tuple) else [reference]
        for actual, ref in zip(outputs, expected, strict=True):
            np.testing.assert_allclose(actual, ref.detach().numpy(), rtol=1e-3, atol=1e-4)
        detector_role = name.startswith("retinaface")
        metadata = (
            {
                "architecture": "RETINAFACE",
                "backbone": "mobilenet0.25",
                "output_semantics": "retinaface_loc_conf_landmarks",
                "landmark_points": 5,
                "min_sizes": [[16, 32], [64, 128], [256, 512]],
                "steps": [8, 16, 32],
                "variance": [0.1, 0.2],
                "confidence_threshold": 0.6,
                "iou_threshold": 0.4,
            }
            if detector_role
            else {
                "architecture": "ADAFACE",
                "backbone": "ir18",
                "embedding_dimension": 512,
                "l2_normalized": True,
                "distance_metric": "cosine",
                "alignment_profile": "arcface_5point_112",
                "source_profile": "cvlface_rgb_webface4m",
            }
        )
        manifest = {
            "schema_version": 1,
            "model_type": "FACE_DETECTOR" if detector_role else "FACE_EMBEDDER",
            "inputs": [{"name": "input", "shape": list(shape), "dtype": "float32"}],
            "outputs": [
                {"name": node.name, "shape": list(value.shape), "dtype": "float32"}
                for node, value in zip(session.get_outputs(), outputs, strict=True)
            ],
            "preprocessing": {
                "layout": "NCHW",
                "color_order": "BGR" if detector_role else "RGB",
                "normalization": "retinaface_bgr_mean_104_117_123"
                if detector_role
                else "adaface_v1",
                "resize_mode": "letterbox" if detector_role else "aligned",
            },
            "metadata": metadata,
            "runtime_compatibility": ["ONNX_CPU"],
        }
        (args.output / (name + ".json")).write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(
            name,
            target.stat().st_size,
            sha256(target.read_bytes()).hexdigest(),
            "CPU parity passed",
            flush=True,
        )


if __name__ == "__main__":
    main()

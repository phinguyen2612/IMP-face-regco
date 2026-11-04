# Local CPU performance profile — 2026-11-04

Host: AMD Ryzen 5 5600H, 6 cores / 12 logical processors; about 7.4 GiB usable
RAM; Radeon RX 5500M. Windows, Python 3.13.5, OpenCV 4.11.0, ONNX Runtime 1.23.2.
The installed ORT providers are Azure and CPU. These measurements use CPU FP32;
GPU acceleration is NOT TESTED.

## Applied configuration

Local `.env` (no credentials in this report):

```dotenv
FR_OPENCV_THREADS=6
FR_ORT_INTRA_OP_THREADS=4
FR_ORT_ALLOW_SPINNING=0
```

`scripts/run-worker.ps1` loads these options and defaults to 960×540 maximum
capture size, 5 inference FPS and 8 retained frames. It accepts `-Width`, `-Height`,
`-RingBufferCapacity` and `-ProcessingFps` overrides. ONNX graph shape, FP32 precision,
confidence thresholds, gallery, identity verification and ROI rules remain unchanged.
YuNet's analysis resize remains 640×480; YOLO's model input remains 640×640.

The raw RGB ring-buffer capacity at the configured maximum changes from
100 × 1280 × 720 × 3 = 263.7 MiB to 8 × 960 × 540 × 3 = 11.9 MiB per camera.
These are calculated payload capacities, not measured process RAM savings. Other
buffers, models and Python memory are additional. A shorter buffer retains less history.

## TESTED — recorded-input adapter benchmark

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_local_inference.py
```

The helper reads local images in place and saves only metadata/timings to
`.runtime/local-inference-benchmark.json`; it does not copy images or write embeddings.
Each candidate has 3 warmups and 20 measured iterations, batch size 1. Timing includes
image decoding/preprocessing, model inference, and adapter postprocessing. Candidates
run sequentially, in one benchmark process, without a live camera. Measurements are
subject to other applications, power state and thermal conditions.

| Adapter | Configuration | Median ms | p95 ms | Mean process CPU ms / call |
|---|---|---:|---:|---:|
| YuNet + SFace | Original 12 threads | 40.107 | 49.336 | 34.375 |
| YuNet + SFace | Selected 6 threads | 37.274 | 38.036 | 44.531 |
| YOLO26n | ORT default threads, spinning on | 68.650 | 78.585 | 300.000 |
| YOLO26n | Selected 4 threads, spinning off | 66.205 | 71.028 | 68.750 |

The face profile trades some CPU time for lower p95 latency. The person profile
uses about 77% less process CPU time per measured call on this input; this is not
a claim of 77% lower system CPU utilization. Four ORT threads were selected over
six because six used more CPU time (89.062 ms/call) and had a higher p95 (73.282 ms).

Face boxes and normalized features matched the original within absolute tolerance
1e-5 on the benchmark image. YOLO box coordinates and confidence matched within
1e-4 on its recorded image. Every tested thread candidate passed these comparisons.
This is limited numerical consistency evidence, not an accuracy evaluation dataset.

YOLO26n ONNX SHA-256:
`e6ca252447799072da198ff89db75bd09278cdfe527fda9dcc1a8ee3cbe53dba`.
YuNet/SFace artifact hashes are fixed in `configuration/models/opencv-face.json`.

## TESTED — automated checks

45 tests passed across simple face comparison, camera recognition API, YOLO/ONNX
session execution, face adapters and worker preview. The new checks execute a real
controlled ONNX graph to verify thread options and reject invalid configuration.
Ruff and mypy passed for the modified runtime code.

## PARTIALLY_TESTED — live deployment

API and worker were restarted with the local profile. Live camera throughput,
multi-camera contention, sustained thermals and resource soak are NOT TESTED:
there was no active camera during this optimization. Configure/activate DroidCam
before making live FPS claims. This report is not a production release gate.

Reference: [ONNX Runtime thread management](https://onnxruntime.ai/docs/performance/tune-performance/threading.html).

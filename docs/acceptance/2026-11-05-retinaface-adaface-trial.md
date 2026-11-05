# RetinaFace MobileNet + AdaFace local trial — 2026-11-05

## Scope and result

`TESTED`: RetinaFace MobileNet 0.25 detection + five-point alignment + AdaFace IR18
WebFace4M embeddings execute on ONNX Runtime CPU FP32. Both roles are registered,
validated, warmed up and assigned ACTIVE. The API comparison flow now uses the
assigned models when `FR_SIMPLE_FACE_ENGINE=registry`; the UI displays actual names.
The worker also supports the RetinaFace profile through its production factory.

`TESTED`: the 9 approved reference images belonging to 3 active profiles were
re-embedded successfully. A model-version/checksum change invalidates gallery,
cached frame decisions and verification state. Reference and query vectors are
created in the same model space; existing SFace vectors are not reused.

`TESTED`: physical webcam device 0, 640×480, 12 frames. All frames contained one
detected face. Verification was PENDING for two frames, then VERIFIED for ten.
Measured comparison latency was 74.87–91.32 ms/frame, including preprocessing,
model execution, reference refresh checks and comparison, excluding capture and
JPEG encoding. Webcam was released afterward. No webcam images were saved.
This is a short functional test, not an identification-accuracy evaluation.

`TESTED`: three upstream AdaFace sample images each produced one face and a
finite normalized 512-dimensional embedding. Observed analysis time 90–143 ms.

`PARTIALLY_TESTED`: live application API and web respond HTTP 200; worker retrieves
all assigned models as ACTIVE without model errors. Browser preview and event
delivery with the new models require an active browser capture or reachable camera.

`NOT TESTED`: distant/small faces and elevated CCTV viewing angles, false accept /
false reject rates, sustained multi-camera throughput, GPU acceleration and soak.
The previously supplied DroidCam endpoint timed out during this trial. Camera
configs were not silently reassigned or enabled.

## Artifacts and provenance

| Role | Source | Source checkpoint SHA-256 | Exported ONNX SHA-256 |
| --- | --- | --- | --- |
| Detector | [biubug6/Pytorch_Retinaface](https://github.com/biubug6/Pytorch_Retinaface), commit `b984b4b775b2c4dced95c1eadd195a5c7d32a60b`, official README Google Drive weights folder, `mobilenet0.25_Final.pth` | `2979b33ffafda5d74b6948cd7a5b9a7a62f62b949cef24e95fd15d2883a65220` | `a9050426a11b405a4bf904a832357a4a524797bd36294607f6f325a451370f87` |
| Embedder | [author's CVLFace release](https://huggingface.co/minchul/cvlface_adaface_ir18_webface4m), revision `0dd53f188fa27968b0a1326970ebf4aeb37ce2ca`, safetensors; matching IR18 architecture from AdaFace commit `c60eaa786a42c03444f3df7096dbaf9d57ae010d` | `3a416518b11ece107b43385fc3678aad1d4f2405fde9f58f0be7f530230e368b` | `eb437e1ca89102809ccd199257a0af45882a2a31bd52a5739cf7ef6beb8e694a` |

Upstream releases retain their own model/data terms. Source checkouts and binaries
remain in ignored `.tools/` and `data/`. Validated ONNX models are stored privately
in the configured model object store, with registry metadata in PostgreSQL.

Provisioning used PyTorch 2.7.1 CPU and torchvision 0.22.1. ONNX opset 17, batch 1,
static detector 640×640 and embedder 112×112. Both exports passed PyTorch/ORT
elementwise comparison at rtol=1e-3, atol=1e-4 on a random input. This establishes
conversion parity for the executed inputs, not model accuracy.

RetinaFace uses BGR minus (104,117,123), top-left letterbox and its own prior-box
decoder. CVLFace release uses **RGB** normalized to [-1,1], unlike legacy AdaFace's
BGR release. RGB is explicitly declared in the embedder manifest. Five landmarks
align the original RGB image to the existing 112×112 template. Adapter owns final
L2 normalization. Tensor shapes, finite values and probability outputs are checked;
malformed outputs raise model errors instead of returning empty detections.

The API keeps original image detail before detector preprocessing and considers
at most 8 faces; pre-NMS candidates are bounded to 300. Current API sample minimum
is 30 source pixels. Detector confidence 0.6 and NMS IoU 0.4 are trial settings.
The comparison threshold 0.45 and identity margin 0.05 remain local trial values,
**not calibrated AdaFace operating points**. Production use requires calibration
and evaluation with separate enrollment and target-camera samples.

## Reproduce and operate

Install provisioning-only `torch`, `torchvision`, `safetensors`; obtain the above
upstream source revisions and checkpoints, verifying hashes before export:

```powershell
.venv/Scripts/python.exe scripts/export_retinaface_adaface.py `
  --retinaface-source .tools/retinaface-source `
  --adaface-source .tools/adaface-source `
  --retinaface-weights data/models/retinaface-adaface/upstream-retinaface/mobilenet0.25_Final.pth `
  --adaface-weights data/models/retinaface-adaface/adaface_ir18_webface4m.safetensors
.venv/Scripts/python.exe scripts/deploy_face_models.py
```

The local operator CLI requires `.env` access and uses the existing registry and
production adapter services. It prepares both models before changing assignments;
activation records follow actual warmup and health checks. Deployment receipt and
previous assignments are in `data/models/retinaface-adaface/deployment-receipt.json`.

Set `FR_SIMPLE_FACE_ENGINE=registry` in local `.env`, restart API and worker, and
visit `http://127.0.0.1:5173/#models` to inspect the selected models. Enable browser
camera in monitoring or supply a reachable DroidCam URL to test the live UI.

To restore the previous local YuNet/SFace comparison, set
`FR_SIMPLE_FACE_ENGINE=opencv` and restart API. Retain model artifacts and receipt;
do not delete deployments as a rollback procedure. Worker role assignments can be
restored to prior ACTIVE deployments through the existing model assignment API/UI.

## Automated validation

- Python suite: 375 passed, 23 skipped (environment/optional integration gates).
- Frontend: 70 passed, 21 files; production build passed.
- Changed runtime modules: mypy passed; Ruff passed.
- Added contract tests for prior decoding, source coordinate restoration, padding,
  malformed output errors, no-face success, BGR mean preprocessing, RGB/BGR AdaFace
  profiles, model-space gallery/cache invalidation and actual UI model names.

Not a production release approval: CCTV accuracy/calibration and long-running
operational gates remain untested.

## Preview flicker follow-up

`TESTED`: the preview keeps its image element across processed frames. A
RECOGNITION_BUSY reply preserves the previous matched image and overlays only
until their original freshness deadline. A changed stream session clears old
overlays immediately. No detection or verified identity is extrapolated onto a
different frame. Seven targeted CameraRecognition tests and a fresh production
build passed after this fix.

`TESTED`: an additional physical-webcam diagnostic detected a face in 20/20
frames, with 19–25 ms detector execution plus decoding per frame. The observed
face size was 163–177 source pixels; this does not validate distant CCTV faces.

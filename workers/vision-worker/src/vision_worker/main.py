import argparse
import json
import os
import time
from hashlib import sha256
from pathlib import Path

from fr_config.models import CameraConfig, FaceRecognitionConfig

from vision_worker.app import VisionWorker
from vision_worker.camera_config import (
    ActiveCamera,
    CameraConfigSynchronizer,
    CameraRuntimeManager,
    HttpActiveCameraProvider,
)
from vision_worker.managed_runtime import RevisionTrackStateCleaner, ThreadedCameraRuntime
from vision_worker.model_delivery import (
    HttpDeploymentProvider,
    ModelDeploymentSynchronizer,
    UnavailableProductionAdapterFactory,
    discover_runtime_capabilities,
)
from vision_worker.runtime.status_publisher import HttpRuntimeStatusPublisher
from vision_worker.video.camera import GStreamerCameraSource
from vision_worker.video.gstreamer_inprocess import GStreamerRtspBackend, load_gstreamer


def _read_feature_config(path: Path) -> tuple[FaceRecognitionConfig, bytes]:
    payload = path.read_bytes()
    return FaceRecognitionConfig.model_validate_json(payload), payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Face Recognition vision worker")
    parser.add_argument("--once", action="store_true", help="Run one smoke/sync cycle")
    parser.add_argument("--camera-config", type=Path)
    parser.add_argument("--feature-config", type=Path)
    parser.add_argument("--control-api-url")
    parser.add_argument("--camera-sync-interval", type=float, default=2.0)
    parser.add_argument("--status-url")
    parser.add_argument("--frame-limit", type=int)
    parser.add_argument("--worker-id", default="worker-local")
    parser.add_argument("--processing-fps", type=float, default=5.0)
    parser.add_argument("--ring-buffer-capacity", type=int, default=100)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()

    if args.camera_sync_interval <= 0:
        parser.error("--camera-sync-interval must be positive")
    if args.control_api_url:
        if args.camera_config is not None:
            parser.error("--camera-config cannot be combined with --control-api-url")
        worker_token = os.getenv("FR_WORKER_INTERNAL_TOKEN")
        if args.feature_config is None or not worker_token:
            parser.error(
                "--feature-config and FR_WORKER_INTERNAL_TOKEN are required with --control-api-url"
            )
        feature, _ = _read_feature_config(args.feature_config)
        gst = load_gstreamer()
        provider = HttpActiveCameraProvider(args.control_api_url, worker_token)
        model_synchronizer = ModelDeploymentSynchronizer(
            HttpDeploymentProvider(args.control_api_url, worker_token),
            discover_runtime_capabilities(),
            UnavailableProductionAdapterFactory(),
        )
        status_url = args.status_url or (
            f"{args.control_api_url.rstrip('/')}/api/v1/runtime/status"
        )

        def factory(config: ActiveCamera) -> ThreadedCameraRuntime:
            camera_feature = feature.model_copy(update={"camera_id": config.id})
            worker = VisionWorker.with_runtime_config(
                camera_feature,
                worker_id=args.worker_id,
                config_revision=config.revision,
                processing_fps=min(args.processing_fps, config.sampling_fps),
                ring_buffer_capacity=args.ring_buffer_capacity,
            )
            backend = GStreamerRtspBackend(gst, width=args.width, height=args.height)
            source = GStreamerCameraSource(
                camera_id=config.id,
                uri=config.rtsp_url,
                codec=config.codec,
                transport="tcp",
                backend=backend,
            )
            return ThreadedCameraRuntime(
                source,
                worker,
                HttpRuntimeStatusPublisher(status_url),
            )

        manager = CameraRuntimeManager(factory, RevisionTrackStateCleaner())
        synchronizer = CameraConfigSynchronizer(provider, manager)
        try:
            while True:
                model_changes = model_synchronizer.sync_once()
                changed = synchronizer.sync_once()
                if args.once:
                    print(
                        json.dumps(
                            {
                                "changed_camera_ids": changed,
                                "processed_model_deployment_ids": model_changes,
                            }
                        )
                    )
                    return
                time.sleep(args.camera_sync_interval)
        finally:
            manager.close_all()

    if (args.camera_config is None) != (args.feature_config is None):
        parser.error("--camera-config and --feature-config must be provided together")

    if args.camera_config is not None and args.feature_config is not None:
        camera_bytes = args.camera_config.read_bytes()
        camera = CameraConfig.model_validate_json(camera_bytes)
        feature, feature_bytes = _read_feature_config(args.feature_config)
        if not camera.enabled or not feature.enabled:
            parser.error("camera and feature configuration must both be enabled")
        if camera.id != feature.camera_id:
            parser.error("camera config id must match feature config camera_id")

        revision = sha256(feature_bytes).hexdigest()[:12]
        worker = VisionWorker.with_runtime_config(
            feature,
            worker_id=args.worker_id,
            config_revision=revision,
            processing_fps=args.processing_fps,
            ring_buffer_capacity=args.ring_buffer_capacity,
        )
        backend = GStreamerRtspBackend(
            load_gstreamer(),
            width=args.width,
            height=args.height,
        )
        source = GStreamerCameraSource(
            camera_id=camera.id,
            uri=str(camera.stream.uri),
            codec=camera.stream.codec,
            transport=camera.stream.transport,
            backend=backend,
        )
        publisher = HttpRuntimeStatusPublisher(args.status_url) if args.status_url else None
        limit = 1 if args.once and args.frame_limit is None else args.frame_limit
        summary = worker.run_camera(source, limit=limit, status_publisher=publisher)
        print(
            json.dumps(
                {
                    "frames_received": summary.frames_received,
                    "frames_processed": summary.frames_processed,
                    "camera_state": summary.camera_state,
                }
            )
        )
        return

    worker = VisionWorker.with_stub_adapters()
    print(json.dumps(worker.run_once()))
    if not args.once:
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

from vision_worker.app import VisionWorker
from vision_worker.inference.stubs import StubFaceDetector, StubFaceEmbedder, StubPersonDetector
from vision_worker.video.frame import VideoFrame


def test_stub_pipeline_is_deterministic_and_has_no_external_dependency() -> None:
    frame = VideoFrame(camera_id="cam-01", stream_session_id="session-01", sequence=1)

    first = VisionWorker.with_stub_adapters().process_frame(frame)
    second = VisionWorker.with_stub_adapters().process_frame(frame)

    assert first == second
    assert first.camera_id == "cam-01"
    assert first.track_results == []


def test_stub_adapters_report_their_non_production_kind() -> None:
    assert StubPersonDetector().adapter_kind == "stub"
    assert StubFaceDetector().adapter_kind == "stub"
    assert StubFaceEmbedder().adapter_kind == "stub"


def test_worker_once_reports_ready_without_camera_or_models() -> None:
    status = VisionWorker.with_stub_adapters().run_once()

    assert status["status"] == "ready"
    assert status["inference_mode"] == "stub"
    assert status["camera_count"] == 0
    assert status["worker_health"] == "degraded"
    assert status["ring_buffer_frames"] == 0
    assert status["active_config_revision"] is None

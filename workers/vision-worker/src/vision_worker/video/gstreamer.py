import subprocess
from time import monotonic_ns
from typing import IO, Protocol
from urllib.parse import urlsplit

from vision_worker.video.frame import VideoFrame


class ProcessHandle(Protocol):
    stdout: IO[bytes] | None
    returncode: int | None

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def kill(self) -> None: ...


class ProcessFactory(Protocol):
    def __call__(
        self,
        args: list[str],
        *,
        stdout: int,
        stderr: int | None,
        shell: bool,
    ) -> ProcessHandle: ...


def _start_process(
    args: list[str],
    *,
    stdout: int,
    stderr: int | None,
    shell: bool,
) -> ProcessHandle:
    return subprocess.Popen(args, stdout=stdout, stderr=stderr, shell=shell)


class SubprocessGStreamerBackend:
    """Reads fixed-size RGB frames from a shell-free gst-launch pipeline."""

    def __init__(
        self,
        executable: str,
        width: int,
        height: int,
        decoder: str,
        converter: str,
        latency_ms: int = 200,
        popen_factory: ProcessFactory = _start_process,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("GStreamer output dimensions must be positive")
        self._executable = executable
        self._width = width
        self._height = height
        self._decoder = decoder
        self._converter = converter
        self._latency_ms = latency_ms
        self._popen_factory = popen_factory
        self._process: ProcessHandle | None = None

    def open(self, uri: str, codec: str, transport: str) -> None:
        self.close()
        parsed = urlsplit(uri)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("credential-bearing RTSP requires in-process GStreamer")
        normalized_codec = codec.upper()
        if normalized_codec not in {"H264", "H265"}:
            raise ValueError("GStreamer backend supports H264 or H265")
        if transport not in {"tcp", "udp"}:
            raise ValueError("GStreamer RTSP transport must be tcp or udp")

        depay = "rtph264depay" if normalized_codec == "H264" else "rtph265depay"
        parser = "h264parse" if normalized_codec == "H264" else "h265parse"
        caps = f"video/x-raw,format=RGB,width={self._width},height={self._height}"
        args = [
            self._executable,
            "-q",
            "rtspsrc",
            f"location={uri}",
            f"protocols={transport}",
            f"latency={self._latency_ms}",
            "!",
            depay,
            "!",
            parser,
            "!",
            self._decoder,
            "!",
            self._converter,
            "!",
            "videoscale",
            "!",
            caps,
            "!",
            "fdsink",
            "fd=1",
        ]
        self._process = self._popen_factory(
            args,
            stdout=subprocess.PIPE,
            stderr=None,
            shell=False,
        )

    def read(self, camera_id: str, session_id: str, sequence: int) -> VideoFrame | None:
        process = self._process
        if process is None or process.stdout is None:
            raise RuntimeError("GStreamer pipeline is not open")
        frame_size = self._width * self._height * 3
        payload = self._read_exact(process.stdout, frame_size)
        if len(payload) != frame_size:
            return None
        return VideoFrame(
            camera_id=camera_id,
            stream_session_id=session_id,
            sequence=sequence,
            timestamp_ms=monotonic_ns() // 1_000_000,
            width=self._width,
            height=self._height,
            pixel_format="RGB",
            payload=payload,
        )

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)

    @staticmethod
    def _read_exact(stream: IO[bytes], size: int) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = stream.read(remaining)
            if not chunk:
                break
            chunks.append(bytes(chunk))
            remaining -= len(chunk)
        return b"".join(chunks)

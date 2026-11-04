"""Bounded MJPEG reader for the DroidCam /video endpoint."""

from io import BytesIO
from queue import Empty, Full, Queue
from threading import Event, Thread
from time import monotonic_ns

import httpx
from PIL import Image, UnidentifiedImageError

from vision_worker.video.camera import FramePending
from vision_worker.video.frame import VideoFrame


class DroidCamBackend:
    def __init__(self, width: int, height: int, client: httpx.Client | None = None) -> None:
        self._width, self._height = width, height
        self._provided = client
        self._client: httpx.Client | None = None
        self._stop = Event()
        self._latest: Queue[tuple[int, int, int, bytes]] = Queue(maxsize=1)
        self._thread: Thread | None = None
        self._error: str | None = None

    def open(self, uri: str, codec: str, transport: str) -> None:
        self.close()
        self._stop.clear()
        self._error = None
        self._latest = Queue(maxsize=1)
        self._client = self._provided or httpx.Client(
            timeout=httpx.Timeout(3.0, read=2.0), follow_redirects=False, trust_env=False
        )
        self._thread = Thread(
            target=self._receive, args=(uri,), daemon=True, name="droidcam-reader"
        )
        self._thread.start()

    def _receive(self, uri: str) -> None:
        client = self._client
        assert client is not None
        try:
            with client.stream("GET", uri) as response:
                if response.status_code in {401, 403}:
                    raise RuntimeError("DROIDCAM_AUTHENTICATION_FAILED")
                response.raise_for_status()
                buffer = bytearray()
                for chunk in response.iter_bytes():
                    if self._stop.is_set():
                        return
                    buffer.extend(chunk)
                    if len(buffer) > 2 * 1024 * 1024:
                        raise RuntimeError("DROIDCAM_FRAME_TOO_LARGE")
                    while True:
                        start = buffer.find(b"\xff\xd8")
                        if start < 0:
                            # Retain a possible JPEG marker split across chunks.
                            buffer[:] = buffer[-1:]
                            break
                        if start:
                            del buffer[:start]
                        end = buffer.find(b"\xff\xd9", 2)
                        if end < 0:
                            break
                        jpeg = bytes(buffer[: end + 2])
                        del buffer[: end + 2]
                        self._offer(jpeg)
                if not self._stop.is_set():
                    raise RuntimeError("DROIDCAM_STREAM_ENDED")
        except httpx.TimeoutException:
            self._error = "DROIDCAM_TIMEOUT"
        except httpx.HTTPError:
            self._error = "DROIDCAM_UNREACHABLE"
        except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
            self._error = "DROIDCAM_INVALID_FRAME"
        except RuntimeError as error:
            self._error = str(error)
        except Exception:
            self._error = "DROIDCAM_STREAM_ERROR"

    def _offer(self, jpeg: bytes) -> None:
        with Image.open(BytesIO(jpeg)) as image:
            if image.width * image.height > 16_000_000:
                raise ValueError("oversized frame")
            image.thumbnail((self._width, self._height))
            rgb = image.convert("RGB")
            frame = (rgb.width, rgb.height, monotonic_ns() // 1_000_000, rgb.tobytes())
        try:
            self._latest.put_nowait(frame)
        except Full:
            try:
                self._latest.get_nowait()
            except Empty:
                pass
            self._latest.put_nowait(frame)

    def read(self, camera_id: str, session_id: str, sequence: int) -> VideoFrame | None:
        if self._stop.is_set():
            return None
        try:
            width, height, timestamp, rgb = self._latest.get(timeout=0.2)
        except Empty:
            if self._error:
                raise RuntimeError(self._error) from None
            raise FramePending from None
        return VideoFrame(camera_id, session_id, sequence, timestamp, width, height, "RGB", rgb)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=4)
            if self._thread.is_alive():
                raise RuntimeError("DROIDCAM_SHUTDOWN_TIMEOUT")
            self._thread = None
        if self._client is not None and self._provided is None:
            self._client.close()
        self._client = None

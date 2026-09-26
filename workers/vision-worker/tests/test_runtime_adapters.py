from pathlib import Path

import pytest
from fr_domain.models import TrackKey
from vision_worker.evidence.storage import LocalBlobStorage
from vision_worker.runtime.track_store import InMemoryTrackStore, TrackState


def test_local_blob_storage_round_trip_and_delete(tmp_path: Path) -> None:
    storage = LocalBlobStorage(tmp_path)

    key = storage.put("events/event-1/snapshot.jpg", b"image-bytes")

    assert key == "events/event-1/snapshot.jpg"
    assert storage.get(key) == b"image-bytes"
    storage.delete(key)
    assert not (tmp_path / key).exists()


def test_local_blob_storage_rejects_path_escape(tmp_path: Path) -> None:
    storage = LocalBlobStorage(tmp_path)

    with pytest.raises(ValueError, match="escapes"):
        storage.put("../outside.bin", b"unsafe")


def test_track_store_evicts_only_expired_camera_scoped_tracks() -> None:
    store = InMemoryTrackStore(ttl_ms=1000)
    expired_key = TrackKey("cam-01", "session-01", 7)
    active_key = TrackKey("cam-02", "session-01", 7)
    store.put(TrackState(expired_key, first_seen_ms=0, last_seen_ms=1000))
    store.put(TrackState(active_key, first_seen_ms=1000, last_seen_ms=1900))

    count = store.evict_expired(now_ms=2001)

    assert count == 1
    assert store.get(expired_key) is None
    assert store.get(active_key) is not None


def test_track_store_creates_touches_and_expires_track_lifecycle() -> None:
    store = InMemoryTrackStore(ttl_ms=1000)
    key = TrackKey("cam-01", "session-01", 9)

    created = store.get_or_create(key, seen_at_ms=100)
    touched = store.touch(key, seen_at_ms=900)

    assert created is touched
    assert touched.first_seen_ms == 100
    assert touched.last_seen_ms == 900
    assert store.active_count == 1
    assert store.evict_expired(now_ms=1900) == 0
    assert store.evict_expired(now_ms=1901) == 1
    assert store.active_count == 0


def test_track_store_rejects_non_positive_ttl() -> None:
    with pytest.raises(ValueError, match="positive"):
        InMemoryTrackStore(ttl_ms=0)

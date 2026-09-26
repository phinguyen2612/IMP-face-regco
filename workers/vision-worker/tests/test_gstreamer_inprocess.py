from vision_worker.video.gstreamer_inprocess import GStreamerRtspBackend


class Element:
    def __init__(self):
        self.properties = {}

    def set_property(self, name, value):
        self.properties[name] = value

    def emit(self, *args):
        return None


class Pipeline:
    def __init__(self):
        self.source = Element()
        self.sink = Element()
        self.states = []

    def get_by_name(self, name):
        return self.source if name == "source" else self.sink

    def set_state(self, state):
        self.states.append(state)


class Gst:
    class State:
        PLAYING = "PLAYING"
        NULL = "NULL"

    def __init__(self):
        self.description = None
        self.pipeline = Pipeline()

    def parse_launch(self, description):
        self.description = description
        return self.pipeline


def test_in_process_gstreamer_sets_secret_as_property_not_pipeline_or_process_argument():
    gst = Gst()
    backend = GStreamerRtspBackend(gst, width=640, height=480)
    secret = "rtsp://alice:password@camera.local/stream"
    backend.open(secret, "AUTO", "tcp")
    assert secret not in gst.description
    assert gst.pipeline.source.properties["location"] == secret
    assert "appsink name=sink" in gst.description
    assert backend.uses_subprocess is False
    backend.close()

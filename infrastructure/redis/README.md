# Redis boundary

Redis is optional for the one-worker MVP. Its intended uses are configuration revision
notifications, worker heartbeat/camera lease, event fan-out, and short-lived operational
status. It is not the primary TrackState store or a video-frame transport.

CREATE TABLE IF NOT EXISTS cameras (
 id text PRIMARY KEY,
 name text NOT NULL,
 protected_rtsp_url bytea NOT NULL,
 redacted_rtsp_url text NOT NULL,
 codec text NOT NULL CHECK (codec IN ('AUTO','H264','H265')),
 enabled boolean NOT NULL,
 sampling_fps double precision NOT NULL CHECK (sampling_fps > 0),
 lifecycle text NOT NULL CHECK (lifecycle IN ('DRAFT','ACTIVE')),
 revision text NOT NULL
);

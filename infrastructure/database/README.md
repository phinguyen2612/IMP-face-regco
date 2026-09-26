# PostgreSQL boundary

PostgreSQL persists encrypted camera configuration and model-management metadata through
`001_cameras.sql` and `002_model_management.sql`. Model definitions, immutable version
metadata, deployments, and active role assignments are stored as rows. Multi-megabyte
ONNX/TensorRT binaries are never stored in PostgreSQL; only artifact metadata and the
backend-controlled storage key are persisted.

Runtime TrackState, frame results, and live model health remain runtime state. A deployment
row marked active is not sufficient evidence that a worker has loaded or warmed the model;
the runtime endpoint reports those states separately.
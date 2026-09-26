export type RecognitionState = "PENDING" | "VERIFIED" | "UNCERTAIN" | "UNKNOWN";

export interface MessageEnvelope<TPayload> {
  schema_version: 1;
  message_id: string;
  type: string;
  timestamp: string;
  camera_id: string | null;
  payload: TPayload;
}

export interface RuntimeStatus {
  worker_id: string;
  camera_id: string;
  camera_state:
    | "DISABLED"
    | "DISCONNECTED"
    | "CONNECTING"
    | "CONNECTED"
    | "RECONNECTING"
    | "ERROR"
    | "FAILED"
    | "STOPPED";
  input_fps: number;
  processed_fps: number;
  dropped_frames: number;
  active_tracks: number;
  ring_buffer_frames: number;
  ring_buffer_capacity: number;
  worker_health: "healthy" | "degraded" | "unhealthy";
  active_config_revision: string | null;
  stream_session_id: string | null;
  reconnect_count: number;
  last_connected_at: string | null;
  last_frame_at: string | null;
  error_category: string | null;
}

export type CameraCodec = "AUTO" | "H264" | "H265";

export interface CameraPublic {
  id: string;
  name: string;
  source_type: "rtsp";
  rtsp_url: string;
  codec: CameraCodec;
  enabled: boolean;
  sampling_fps: number;
  lifecycle: "DRAFT" | "ACTIVE";
  revision: string;
}

export interface CameraInput {
  name: string;
  rtsp_url: string;
  codec: CameraCodec;
  enabled: boolean;
  sampling_fps: number;
}

export interface CameraConnectionResult {
  status: string;
  error_category: string | null;
}

export type ModelType = "PERSON_DETECTOR" | "FACE_DETECTOR" | "FACE_EMBEDDER";
export type DeploymentBackend = "AUTO" | "ONNX_CPU" | "ONNX_CUDA" | "TENSORRT";

export interface ModelVersionPublic {
  id: string;
  version: string;
  format: "ONNX" | "TENSORRT_ENGINE";
  checksum: string;
  size_bytes: number;
  validation_status: "UPLOADED" | "VALIDATING" | "VALID" | "INVALID";
  validation_error: string | null;
  manifest: { inputs: Array<{ name: string; shape: Array<number | string>; dtype: string }> };
}

export interface ModelDeploymentPublic {
  id: string;
  model_version_id: string;
  backend: DeploymentBackend;
  resolved_backend: DeploymentBackend | null;
  precision: string;
  status: "DRAFT" | "ACTIVATION_PENDING" | "ACTIVE" | "INACTIVE" | "ERROR";
  error_category: string | null;
}

export interface ModelDefinitionPublic {
  id: string;
  name: string;
  model_type: ModelType;
  framework: string;
  description: string;
  versions: ModelVersionPublic[];
  deployments: ModelDeploymentPublic[];
}

export interface RecognitionReadiness {
  status: "READY" | "NOT_READY";
  reasons: string[];
  assignments: Partial<Record<ModelType, string>>;
  vector_index_status: string;
}
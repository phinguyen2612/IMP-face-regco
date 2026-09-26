import type {
  CameraConnectionResult,
  CameraInput,
  CameraPublic,
  MessageEnvelope,
  RuntimeStatus,
  ModelDefinitionPublic,
  ModelDeploymentPublic,
  ModelType,
  DeploymentBackend,
  RecognitionReadiness
} from "./contracts";

export interface HealthStatus {
  service: string;
  status: string;
  external_dependencies: string;
  camera_persistence?: string;
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthStatus> {
  return json("/health");
}

export function listCameras(): Promise<CameraPublic[]> {
  return json<{ items: CameraPublic[] }>("/api/v1/cameras").then((value) => value.items);
}

export function createCamera(input: CameraInput): Promise<CameraPublic> {
  return json("/api/v1/cameras", { method: "POST", body: JSON.stringify(input) });
}

export function updateCamera(
  id: string,
  input: Partial<CameraInput>
): Promise<CameraPublic> {
  return json(`/api/v1/cameras/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export function testCamera(id: string): Promise<CameraConnectionResult> {
  return json(`/api/v1/cameras/${id}/test-connection`, { method: "POST" });
}

export function activateCamera(id: string): Promise<CameraPublic> {
  return json(`/api/v1/cameras/${id}/activate`, { method: "POST" });
}

export function connectRuntimeStatus(
  onStatus: (status: RuntimeStatus) => void
): () => void {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws`);
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(String(event.data)) as MessageEnvelope<RuntimeStatus>;
    if (message.type === "runtime.status") onStatus(message.payload);
  });
  return () => socket.close();
}

export function listModels(): Promise<ModelDefinitionPublic[]> {
  return json<{ items: ModelDefinitionPublic[] }>("/api/v1/models").then((value) => value.items);
}

export function createModel(input: {
  name: string;
  model_type: ModelType;
  framework: string;
  description?: string;
}): Promise<ModelDefinitionPublic> {
  return json("/api/v1/models", { method: "POST", body: JSON.stringify(input) });
}

export async function uploadModelVersion(
  definitionId: string,
  version: string,
  manifest: object,
  file: File
): Promise<void> {
  const body = new FormData();
  body.set("version", version);
  body.set("manifest", JSON.stringify(manifest));
  body.set("file", file);
  const response = await fetch(`/api/v1/models/${definitionId}/versions`, {
    method: "POST",
    body
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(detail?.detail ?? `Upload failed: ${response.status}`);
  }
}

export function createModelDeployment(
  versionId: string,
  backend: DeploymentBackend
): Promise<ModelDeploymentPublic> {
  return json(`/api/v1/model-versions/${versionId}/deployments`, {
    method: "POST",
    body: JSON.stringify({ backend, precision: "FP32" })
  });
}

export function activateModelDeployment(id: string): Promise<ModelDeploymentPublic> {
  return json(`/api/v1/deployments/${id}/activate`, { method: "POST" });
}

export function assignModel(modelType: ModelType, deploymentId: string): Promise<void> {
  return json("/api/v1/model-assignments", {
    method: "PUT",
    body: JSON.stringify({ model_type: modelType, deployment_id: deploymentId })
  }).then(() => undefined);
}

export function getRecognitionReadiness(): Promise<RecognitionReadiness> {
  return json("/api/v1/recognition/readiness");
}
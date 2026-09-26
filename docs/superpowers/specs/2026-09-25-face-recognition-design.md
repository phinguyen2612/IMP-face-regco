# Face Recognition System Design

## Scope

Build only the Face Recognition flow approved in Phase 1: RTSP ingestion, person
detection, BoT-SORT tracking, face detection, ROI and quality filtering, alignment,
embedding, vector search, multi-frame verification, identity decision, policy,
events, evidence, API, WebSocket, and React UI.

The MVP targets one IP camera on NVIDIA Jetson AGX Orin 32GB while retaining
interfaces for multiple cameras and NVIDIA GPU servers. It does not include other
IOC business features, anti-spoofing, authentication, or production model artifacts.

## Runtime boundaries

- FastAPI control plane owns persistent configuration and business contracts.
- A vision worker owns camera-local video, tracking, recognition, and track state.
- React consumes REST and WebSocket contracts.
- PostgreSQL is the future persistent store; Redis is used only where coordination
  or fan-out is useful; track state stays in process for the MVP.
- Local evidence storage implements a storage abstraction that can later use S3 or MinIO.

## Core rules

- Models are selected using model definition, version, and deployment identifiers.
- Raw runtime paths and GPU configuration are never UI fields.
- Recognition is scheduled by track and is not performed on every frame.
- A final identity never comes from one frame.
- Enrollment supports multiple embeddings per person.
- FAISS implements a replaceable vector-store contract.
- Every published configuration is immutable and versioned.
- Detected face crops are not permanently stored by default.

## Scaffold boundary

The initial scaffold provides validated configuration models, domain contracts,
inference/vector/storage interfaces, deterministic stub adapters, API health and
configuration-validation routes, worker startup, a React shell, and tests. Real
GStreamer, TensorRT, YOLO, SCRFD, AdaFace, BoT-SORT, FAISS persistence, PostgreSQL,
Redis, evidence encoding, and WebSocket delivery remain explicit integration work.

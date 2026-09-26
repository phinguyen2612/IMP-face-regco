# Local development

PostgreSQL and Redis are available through the local Compose profile. Ports bind to
loopback only, defaults are explicitly development-only, and both services include
health checks.

```bash
docker compose --env-file infrastructure/local/.env.example \
  -f infrastructure/local/compose.yaml up -d --wait
```

Generate backend-only local secrets instead of committing values:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set `FR_POSTGRES_DSN`, `FR_CAMERA_ENCRYPTION_KEY`, and
`FR_WORKER_INTERNAL_TOKEN` in the API process. The worker receives only the internal
token and control API base URL. RTSP credentials are created and edited in the web UI;
they are never environment variables or command-line arguments.

When PostgreSQL settings are absent, the API reports `camera_persistence=in_memory` in
health for dependency-free development. Production camera persistence requires
`camera_persistence=postgresql`.

GStreamer and its Python introspection bindings are system dependencies. Install the
CPU decode plugins for the host OS; NVIDIA plugins are not required. The worker loads
GStreamer lazily only when a real camera runtime or connection test starts.

Managed camera worker example:

```bash
python -m vision_worker.main --control-api-url http://127.0.0.1:8000 \
  --feature-config config/feature.json
```

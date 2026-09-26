import { useEffect, useState } from "react";

import { connectRuntimeStatus, getHealth, type HealthStatus } from "../api/client";
import type { RuntimeStatus } from "../api/contracts";
import { CameraPanel } from "../features/cameras/CameraPanel";
import { ModelsPanel } from "../features/models/ModelsPanel";

const configurationAreas = [
  "Camera and models",
  "Recognition ROI",
  "Face quality",
  "Verification and timing",
  "Schedule and policy",
  "Evidence"
];

export function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runtimeStatuses, setRuntimeStatuses] = useState<RuntimeStatus[]>([]);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setError("Control API is unavailable"));
    return connectRuntimeStatus((next) => {
      setRuntimeStatuses((current) => [
        ...current.filter(
          (item) => item.worker_id !== next.worker_id || item.camera_id !== next.camera_id
        ),
        next
      ]);
    });
  }, []);

  return (
    <main>
      <header>
        <p className="eyebrow">JETSON-READY CONTROL PLANE</p>
        <h1>Face Recognition</h1>
        <p>Configuration-first scaffold for track-based, multi-frame identity decisions.</p>
      </header>

      <section className="status" aria-label="System status">
        <span className={health ? "indicator online" : "indicator"} />
        {health ? `${health.service}: ${health.status}` : error ?? "Checking control API..."}
      </section>

      <section>
        <h2>Runtime status</h2>
        <div className="grid">
          {runtimeStatuses.length === 0 ? (
            <article><p>No worker status has been published.</p></article>
          ) : runtimeStatuses.map((runtime) => (
            <article key={`${runtime.worker_id}:${runtime.camera_id}`}>
              <h3>{runtime.camera_id}</h3>
              <p>{runtime.camera_state} · {runtime.worker_health}</p>
              <dl>
                <dt>Input / processed FPS</dt>
                <dd>{runtime.input_fps.toFixed(1)} / {runtime.processed_fps.toFixed(1)}</dd>
                <dt>Dropped frames</dt><dd>{runtime.dropped_frames}</dd>
                <dt>Active tracks</dt><dd>{runtime.active_tracks}</dd>
                <dt>Ring buffer</dt>
                <dd>{runtime.ring_buffer_frames} / {runtime.ring_buffer_capacity}</dd>
                <dt>Config revision</dt>
                <dd>{runtime.active_config_revision ?? "none"}</dd>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <CameraPanel runtimeStatuses={runtimeStatuses} />

      <ModelsPanel />

      <section>
        <h2>Configuration areas</h2>
        <div className="grid">
          {configurationAreas.map((area) => (
            <article key={area}>
              <h3>{area}</h3>
              <p>Contract ready; UI editor follows in the next implementation step.</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

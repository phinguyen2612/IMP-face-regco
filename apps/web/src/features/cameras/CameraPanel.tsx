import { FormEvent, useEffect, useState } from "react";

import {
  activateCamera,
  createCamera,
  listCameras,
  testCamera,
  updateCamera
} from "../../api/client";
import type { CameraCodec, CameraPublic, RuntimeStatus } from "../../api/contracts";

interface CameraPanelProps {
  runtimeStatuses: RuntimeStatus[];
}

export function CameraPanel({ runtimeStatuses }: CameraPanelProps) {
  const [items, setItems] = useState<CameraPublic[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [codec, setCodec] = useState<CameraCodec>("AUTO");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editUrl, setEditUrl] = useState("");
  const [editCodec, setEditCodec] = useState<CameraCodec>("AUTO");
  const [message, setMessage] = useState("");

  async function refresh() {
    try {
      setItems(await listCameras());
    } catch {
      setMessage("Unable to load cameras");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await createCamera({
        name,
        rtsp_url: url,
        codec,
        enabled: true,
        sampling_fps: 5
      });
      setName("");
      setUrl("");
      setMessage("Camera saved as draft. Credential is no longer displayed.");
      await refresh();
    } catch {
      setMessage("Camera validation or save failed");
    }
  }

  function beginEdit(camera: CameraPublic) {
    setEditingId(camera.id);
    setEditName(camera.name);
    setEditCodec(camera.codec);
    setEditUrl("");
  }

  async function saveEdit(camera: CameraPublic) {
    const update: Partial<{
      name: string;
      rtsp_url: string;
      codec: CameraCodec;
    }> = { name: editName, codec: editCodec };
    if (editUrl) update.rtsp_url = editUrl;
    try {
      await updateCamera(camera.id, update);
      setEditUrl("");
      setEditingId(null);
      setMessage("Camera updated as draft; activate it to deliver the new revision.");
      await refresh();
    } catch {
      setMessage("Camera update failed");
    }
  }

  return (
    <section aria-labelledby="camera-heading">
      <h2 id="camera-heading">Cameras</h2>
      <form onSubmit={submit}>
        <label>Camera name<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
        <label>Source<select value="RTSP" disabled><option>RTSP</option></select></label>
        <label>
          RTSP URL
          <input
            type="password"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            required
            autoComplete="new-password"
          />
        </label>
        <label>
          Codec
          <select value={codec} onChange={(event) => setCodec(event.target.value as CameraCodec)}>
            <option>AUTO</option><option>H264</option><option>H265</option>
          </select>
        </label>
        <button type="submit">Add Camera</button>
      </form>
      {message && <p role="status">{message}</p>}
      <div className="grid">
        {items.map((camera) => {
          const runtime = runtimeStatuses.find((item) => item.camera_id === camera.id);
          const editing = editingId === camera.id;
          return (
            <article key={camera.id}>
              {editing ? (
                <>
                  <label>Edit name<input value={editName} onChange={(event) => setEditName(event.target.value)} /></label>
                  <label>
                    Replacement RTSP URL (optional)
                    <input
                      type="password"
                      value={editUrl}
                      onChange={(event) => setEditUrl(event.target.value)}
                      autoComplete="new-password"
                    />
                  </label>
                  <label>
                    Codec
                    <select
                      value={editCodec}
                      onChange={(event) => setEditCodec(event.target.value as CameraCodec)}
                    >
                      <option>AUTO</option><option>H264</option><option>H265</option>
                    </select>
                  </label>
                  <button onClick={() => void saveEdit(camera)}>Save</button>
                  <button onClick={() => { setEditingId(null); setEditUrl(""); }}>Cancel</button>
                </>
              ) : (
                <>
                  <h3>{camera.name}</h3>
                  <p>{camera.rtsp_url}</p>
                  <p>{camera.codec} · {camera.enabled ? "Enabled" : "Disabled"} · {camera.lifecycle}</p>
                  <p>
                    Runtime: {camera.enabled ? (runtime?.camera_state ?? "NOT REPORTED") : "DISABLED"}
                    {runtime ? ` · ${runtime.input_fps.toFixed(1)} FPS · reconnects ${runtime.reconnect_count}` : ""}
                  </p>
                  {runtime?.error_category && <p>Error: {runtime.error_category}</p>}
                  <button onClick={() => beginEdit(camera)}>Edit</button>
                  <button onClick={async () => { await updateCamera(camera.id, { enabled: !camera.enabled }); await refresh(); }}>
                    {camera.enabled ? "Disable" : "Enable"}
                  </button>
                  <button onClick={async () => { const result = await testCamera(camera.id); setMessage(`Connection: ${result.status}`); }}>
                    Test Connection
                  </button>
                  <button
                    disabled={camera.lifecycle === "ACTIVE"}
                    onClick={async () => { await activateCamera(camera.id); await refresh(); }}
                  >
                    Activate
                  </button>
                </>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";

import { sendBrowserFrame, startBrowserSession, stopBrowserSession } from "../../api/browserCamera";
import type { CameraPublic } from "../../api/contracts";

export function BrowserWebcamLive({ camera }: { camera: CameraPublic }) {
  const video = useRef<HTMLVideoElement>(null);
  const media = useRef<MediaStream | null>(null);
  const session = useRef<{ cameraId: string; token: string } | null>(null);
  const generation = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const upload = useRef<AbortController | null>(null);
  const cleanupPromise = useRef(Promise.resolve());
  const [phase, setPhase] = useState<"off" | "opening" | "live">("off");
  const [sent, setSent] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<'user' | 'environment'>('user');
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState('');

  const release = useCallback(() => {
    generation.current += 1;
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    upload.current?.abort(); upload.current = null;
    media.current?.getTracks().forEach(track => track.stop()); media.current = null;
    if (video.current) video.current.srcObject = null;
    const previous = session.current; session.current = null;
    const deletion = previous ? stopBrowserSession(previous.cameraId, previous.token).catch(() => {}) : Promise.resolve();
    cleanupPromise.current = Promise.all([cleanupPromise.current, deletion]).then(() => {});
    return cleanupPromise.current;
  }, []);

  const stop = useCallback(() => { void release(); setPhase("off"); }, [release]);

  useEffect(() => {
    setPhase("off"); setError(null);
    return () => { void release(); };
  }, [camera.id, camera.revision, camera.enabled, camera.lifecycle, release]);

  useEffect(() => {
    const hidden = () => { if (document.visibilityState === "hidden") stop(); };
    window.addEventListener("pagehide", stop);
    document.addEventListener("visibilitychange", hidden);
    return () => {
      window.removeEventListener("pagehide", stop);
      document.removeEventListener("visibilitychange", hidden);
    };
  }, [stop]);

  async function start() {
    setError(null); setSent(0); setPhase("opening");
    if (!navigator.mediaDevices?.getUserMedia || window.isSecureContext === false) {
      setError("Webcam cần trình duyệt hỗ trợ và địa chỉ localhost hoặc HTTPS."); setPhase("off"); return;
    }
    const request = generation.current;
    try {
      await cleanupPromise.current;
      if (request !== generation.current) return;
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { ...(deviceId ? {deviceId: {exact: deviceId}} : {facingMode: {ideal: facing}}), width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false
      });
      if (request !== generation.current) { stream.getTracks().forEach(track => track.stop()); return; }
      media.current = stream;
      // Device labels become available after the user grants camera permission.
      void navigator.mediaDevices.enumerateDevices?.().then(items => {
        if (request === generation.current) setDevices(items.filter(item => item.kind === 'videoinput'));
      }).catch(() => {});
      stream.getTracks().forEach(track => track.addEventListener("ended", () => {
        if (request !== generation.current) return;
        stop(); setError("Webcam đã ngắt kết nối. Hãy bắt đầu lại để tiếp tục.");
      }, { once: true }));
      if (!video.current) { await release(); return; }
      video.current.srcObject = stream;
      await video.current.play();
      if (request !== generation.current) return;
      const created = await startBrowserSession(camera.id);
      if (request !== generation.current) {
        await stopBrowserSession(camera.id, created.token).catch(() => {}); return;
      }
      session.current = { cameraId: camera.id, token: created.token };
      setPhase("live");
      const canvas = document.createElement("canvas");
      const interval = 1000 / Math.max(1, Math.min(10, camera.sampling_fps));

      const sendNext = async () => {
        if (request !== generation.current) return;
        const element = video.current;
        try {
          if (element?.videoWidth && element.videoHeight) {
            const scale = Math.min(1, 1280 / element.videoWidth, 720 / element.videoHeight);
            canvas.width = Math.max(1, Math.floor(element.videoWidth * scale));
            canvas.height = Math.max(1, Math.floor(element.videoHeight * scale));
            const context = canvas.getContext("2d");
            if (!context) throw new Error("Không đọc được hình ảnh webcam.");
            context.drawImage(element, 0, 0, canvas.width, canvas.height);
            const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, "image/jpeg", 0.75));
            if (request !== generation.current) return;
            if (!blob || blob.size > 1024 * 1024) throw new Error("Không tạo được khung hình phù hợp. Hãy bắt đầu lại webcam.");
            const controller = new AbortController(); upload.current = controller;
            const deadline = setTimeout(() => controller.abort(), 8000);
            try {await sendBrowserFrame(camera.id, created.token, blob, controller.signal);}
            finally {clearTimeout(deadline);}
            if (request !== generation.current) return;
            upload.current = null;
            setSent(value => value + 1);
          }
          if (request === generation.current) timer.current = setTimeout(() => { void sendNext(); }, interval);
        } catch (reason) {
          if (request !== generation.current) return;
          stop();
          setError(reason instanceof DOMException && reason.name === 'AbortError'
            ? 'Máy chủ chưa phản hồi việc gửi khung hình sau 8 giây. Máy chủ có thể đang bận hoặc kết nối bị chậm. Hãy bắt đầu lại.'
            : reason instanceof Error ? reason.message : "Kết nối webcam bị gián đoạn. Hãy bắt đầu lại.");
        }
      };
      void sendNext();
    } catch (reason) {
      if (request !== generation.current) return;
      stop();
      setError(reason instanceof DOMException && reason.name === "NotAllowedError"
        ? "Chưa được cấp quyền camera. Hãy cho phép webcam trong trình duyệt rồi thử lại."
        : reason instanceof DOMException && reason.name === 'NotFoundError'
        ? 'Không tìm thấy thiết bị camera. Kết nối webcam hoặc chọn camera khác rồi thử lại.'
        : reason instanceof DOMException && reason.name === 'NotReadableError'
        ? 'Camera đang bị ứng dụng khác sử dụng hoặc không đọc được. Đóng ứng dụng đang dùng camera rồi thử lại.'
        : reason instanceof DOMException && reason.name === 'OverconstrainedError'
        ? 'Thiết bị camera đã chọn không còn khả dụng. Chọn lại nguồn camera rồi thử lại.'
        : reason instanceof Error ? reason.message : "Không mở được webcam.");
    }
  }

  const allowed = camera.source_type === "webcam" && camera.enabled && camera.lifecycle === "ACTIVE";
  return (
    <div className="browser-webcam-live">
      <p>Webcam của trình duyệt · Tối đa {Math.min(10, camera.sampling_fps)} FPS</p>
      <div className="browser-camera-toolbar">{devices.length > 0 && <label>Thiết bị camera<select disabled={phase !== 'off'} value={deviceId} onChange={event => setDeviceId(event.target.value)}><option value="">Thiết bị mặc định</option>{devices.map((device, index) => <option key={device.deviceId || index} value={device.deviceId}>{device.label || `Camera ${index + 1}`}</option>)}</select></label>}
      <label>Hướng camera<select disabled={phase !== 'off' || !!deviceId} value={facing} onChange={event => setFacing(event.target.value as 'user' | 'environment')}><option value="user">Camera trước / webcam</option><option value="environment">Camera sau điện thoại</option></select></label></div>
      {!allowed && <p>Kích hoạt camera trước khi bắt đầu realtime.</p>}
      {phase === "off" ? <button type="button" disabled={!allowed} onClick={start}>Bắt đầu realtime</button>
        : <button type="button" onClick={stop}>Dừng realtime</button>}
      {phase === "opening" && <p role="status">Đang kết nối webcam…</p>}
      {phase === 'off' && allowed && <p className="registry-help">Bấm Bắt đầu realtime rồi cho phép camera để gửi hình. Camera trình duyệt cần localhost hoặc HTTPS; địa chỉ IP mạng nội bộ qua HTTP không hỗ trợ quyền camera.</p>}
      <video ref={video} aria-label={`Webcam realtime ${camera.name}`} autoPlay muted playsInline hidden={phase !== "live"} />
      <p role="status">{phase === "live" ? `Đang truyền · Đã gửi ${sent} khung hình` : "Webcam đã dừng"}</p>
      <p className="registry-help">Xử lý nhận diện phụ thuộc model đã gán. FPS xử lý và trạng thái worker hiển thị phía trên.</p>
      {error && <p role="alert" className="registry-error">{error}</p>}
    </div>
  );
}

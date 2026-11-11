import {useEffect, useState} from 'react';
import {listCameras} from '../../api/client';
import type {CameraPublic, RuntimeStatus} from '../../api/contracts';
import {BrowserWebcamLive} from '../cameras/BrowserWebcamLive';
import {CameraRecognition} from '../cameras/CameraRecognition';
import {Icon} from '../../ui/Icon';
import {DataState} from '../../ui/DataState';
import {StatusBadge} from '../../ui/StatusBadge';

export function cameraRuntimeLabel(camera: CameraPublic, runtime?: RuntimeStatus): string {
  if (!camera.enabled) return 'Đã tắt';
  if (camera.lifecycle !== 'ACTIVE') return 'Chưa áp dụng cấu hình';
  if (camera.source_type === 'webcam' && !runtime) return 'Nguồn webcam trình duyệt';
  if (!runtime) return 'Chưa nhận trạng thái worker';
  if (!runtime.last_frame_at || Date.now() - Date.parse(runtime.last_frame_at) > 15000) return 'Chưa có hình mới';
  if (runtime.active_config_revision !== camera.revision) return 'Đang chờ phiên bản cấu hình';
  return runtime.camera_state === 'CONNECTED' ? 'Đang nhận hình' : 'Kết nối cần kiểm tra';
}

export function MonitoringPage({statuses, overview = false}: {statuses: RuntimeStatus[]; overview?: boolean}) {
  const [cameras, setCameras] = useState<CameraPublic[]>([]);
  const [selected, setSelected] = useState(() => {try {return sessionStorage.getItem('monitor-camera') ?? '';} catch {return '';}});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [, tick] = useState(0);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const rows = await listCameras();
        if (alive) {
          setCameras(rows); setError('');
          setSelected(current => rows.some(c => c.id === current) ? current : rows.find(c => c.enabled && c.lifecycle === 'ACTIVE')?.id ?? rows[0]?.id ?? '');
        }
      } catch {if (alive) setError('Không tải được camera. Đang thử kết nối lại…');}
      finally {if (alive) {setLoading(false); timer = setTimeout(() => void refresh(), 10000);}}
    }
    void refresh();
    const clock = setInterval(() => tick(value => value + 1), 5000);
    return () => {alive = false; clearTimeout(timer); clearInterval(clock);};
  }, []);
  const camera = cameras.find(item => item.id === selected);
  const runtime = statuses.find(item => item.camera_id === selected);
  useEffect(() => {try {sessionStorage.setItem('monitor-camera', selected);} catch { /* Optional preference. */ }}, [selected]);
  return <section className="operations-workspace">
    {overview && <div className="workspace-welcome"><div><p className="eyebrow">KHÔNG GIAN VẬN HÀNH</p><h2>Mọi nguồn hình, cùng một góc nhìn.</h2><p>Kiểm tra camera, theo dõi nhận diện và tra cứu minh chứng tại một nơi.</p></div><a className="quiet-action" href="#livewall"><Icon name="grid"/>Mở Livewall <Icon name="arrow"/></a></div>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {loading ? <DataState loading title="Đang tải camera…"/> : !cameras.length ? !error && <article className="empty-state"><Icon name="camera"/><h2>Bắt đầu với camera đầu tiên</h2><p>Thêm nguồn hình, kiểm tra kết nối rồi áp dụng cấu hình để bắt đầu giám sát.</p><a href="#cameras" className="primary-action">Thiết lập camera</a></article> : <>
      {overview && <div className="operations-summary"><div><span><Icon name="camera"/>Camera đã cấu hình</span><strong>{cameras.length}</strong><small>Nguồn hình trong hệ thống</small></div><div><span><Icon name="check"/>Cấu hình đã kích hoạt</span><strong>{cameras.filter(c => c.enabled && c.lifecycle === 'ACTIVE').length}</strong><small>Đã bật và áp dụng cấu hình</small></div><div><span><Icon name="settings"/>Cần áp dụng cấu hình</span><strong>{cameras.filter(c => c.lifecycle === 'DRAFT').length}</strong><small>Camera đang ở bản nháp</small></div></div>}
      <div className="operations-primary">
        <div className="monitor-toolbar"><label>Camera đang xem<select value={selected} onChange={event => setSelected(event.target.value)}>{cameras.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><div className="monitor-view-actions"><a className="quiet-action" href="#livewall"><Icon name="grid"/>Mở Livewall</a><a className="quiet-action" href="#cameras"><Icon name="settings"/>Cấu hình camera</a></div></div>
        {camera && <article className="monitor-stage"><header className="monitor-stage-heading"><div><span className="camera-heading-icon"><Icon name="camera"/></span><div><h2>{camera.name}</h2><p>Camera đang xem</p></div></div><StatusBadge tone={cameraRuntimeLabel(camera, runtime) === "Đang nhận hình" ? "success" : "neutral"}>{cameraRuntimeLabel(camera, runtime)}</StatusBadge></header>{camera.source_type === 'webcam' && <div className="monitor-webcam-controls"><BrowserWebcamLive camera={camera}/></div>}<div className="monitor-feed"><CameraRecognition key={camera.id} camera={camera} roiPolygon={camera.roi_polygon}/></div><div className="camera-status-strip"><div><span>Hình gần nhất</span><strong>{runtime?.last_frame_at ? new Date(runtime.last_frame_at).toLocaleTimeString('vi-VN', {timeZone:'Asia/Ho_Chi_Minh'}) : 'Chưa có dữ liệu'}</strong></div><div><span>Cảnh báo người lạ</span><strong>{camera.unknown_alert_frames ?? 5} frame liên tiếp</strong></div><div><span>Thời hạn lưu ảnh</span><strong>{camera.evidence_retention_days ?? 30} ngày</strong></div><a href="#alerts">Evidence người lạ <Icon name="arrow"/></a></div><details className="runtime-details"><summary>Thông số vận hành</summary><dl><dt>Tốc độ xử lý</dt><dd>{runtime ? `${runtime.processed_fps.toFixed(1)} FPS` : 'Chưa có dữ liệu'}</dd><dt>Model người</dt><dd>{runtime?.person_detector_runtime?.model_version ?? 'Chưa có báo cáo'}</dd></dl></details></article>}
      </div>
    </>}
  </section>;
}

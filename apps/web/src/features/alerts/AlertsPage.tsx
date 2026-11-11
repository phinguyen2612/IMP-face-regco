import {useEffect, useState} from 'react';
import {listCameras} from '../../api/client';
import type {CameraPublic} from '../../api/contracts';
import {FaceEventsPanel} from '../history/FaceEventsPanel';

export function AlertsPage() {
  const [cameras, setCameras] = useState<CameraPublic[]>([]);
  const [cameraId, setCameraId] = useState(() => new URLSearchParams(window.location.hash.split('?')[1]).get('camera') ?? '');
  const [start, setStart] = useState(() => new URLSearchParams(window.location.hash.split('?')[1]).get('start') ?? '');
  const [end, setEnd] = useState(() => new URLSearchParams(window.location.hash.split('?')[1]).get('end') ?? '');
  const [error, setError] = useState('');
  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.split('?')[1]);
    for (const key of ['camera', 'start', 'end']) params.delete(key);
    if (cameraId) params.set('camera', cameraId);
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    window.history.replaceState(null, '', `#alerts${params.size ? `?${params}` : ''}`);
  }, [cameraId, start, end]);
  useEffect(() => {let alive = true; listCameras().then(rows => {if (alive) setCameras(rows);}).catch(() => {if (alive) setError('Không tải được bộ lọc camera.');}); return () => {alive = false;};}, []);
  return <section className="alerts-workspace">
    {error && <p role="alert">{error}</p>}
    <div className="filter-surface"><div className="filter-toolbar"><label>Camera<select value={cameraId} onChange={e => setCameraId(e.target.value)}><option value="">Tất cả camera</option>{cameras.map(camera => <option key={camera.id} value={camera.id}>{camera.name}</option>)}</select></label><label>Từ ngày<input type="date" value={start} onChange={e => setStart(e.target.value)}/></label><label>Đến ngày<input type="date" value={end} min={start} onChange={e => setEnd(e.target.value)}/></label>{(cameraId || start || end) && <button type="button" onClick={() => {setCameraId(''); setStart(''); setEnd('');}}>Xóa bộ lọc</button>}</div><p className="filter-caption"><span className="product-badge tone-warning">Cảnh báo người lạ</span><span>Tự cập nhật mỗi 3 giây · Giờ Việt Nam</span></p></div>
    {start && end && start > end ? <p role="alert">Ngày kết thúc phải từ ngày bắt đầu trở đi.</p> : <FaceEventsPanel cameraId={cameraId || undefined} kind="UNKNOWN_ALERT" start={start} end={end} report/>}
  </section>;
}

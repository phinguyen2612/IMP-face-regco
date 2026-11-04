import {useEffect, useRef, useState} from 'react';
import {apiFetch} from '../../api/client';
import type {FacePresenceEvent} from '../../api/simpleRecognition';

const LIMIT = 50;

export function groupNotifications(events: FacePresenceEvent[]) {
  const groups: {event: FacePresenceEvent; ids: string[]}[] = [];
  for (const event of [...events].sort((a,b) => Date.parse(b.recognized_at)-Date.parse(a.recognized_at))) {
    const group = groups.find(item => item.event.camera_id && item.event.camera_id === event.camera_id && item.event.kind === event.kind && Math.abs(Date.parse(item.event.recognized_at)-Date.parse(event.recognized_at)) <= 30000);
    if (group) group.ids.push(event.id);
    else groups.push({event, ids: [event.id]});
  }
  return groups;
}

export function CameraNotifications({userId}: {userId: string}) {
  const storageKey = `camera-notifications-read:${userId}`;
  const [readIds, setReadIds] = useState<string[]>(() => {
    try {
      const value: unknown = JSON.parse(localStorage.getItem(storageKey) ?? '[]');
      return Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string').slice(-200) : [];
    } catch {return [];}
  });
  const [events, setEvents] = useState<FacePresenceEvent[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController;
    async function refresh() {
      if (document.visibilityState === 'hidden') {timer = setTimeout(() => void refresh(), 3000); return;}
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      try {
        const response = await apiFetch(`/api/v1/recognition/face-events?limit=${LIMIT}`, {signal: controller.signal, cache: 'no-store'});
        if (!response.ok) throw new Error('FETCH_FAILED');
        const rows: FacePresenceEvent[] = await response.json();
        if (!disposed) {setEvents([...new Map(rows.slice(0, LIMIT).map(row => [row.id, row])).values()]); setError('');}
      } catch {
        if (!disposed) setError('Không cập nhật được thông báo. Đang thử lại…');
      } finally {
        clearTimeout(timeout);
        if (!disposed) {setLoading(false); timer = setTimeout(() => void refresh(), 3000);}
      }
    }
    void refresh();
    return () => {disposed = true; clearTimeout(timer); controller?.abort();};
  }, []);

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {if (!root.current?.contains(event.target as Node)) setOpen(false);};
    const escape = (event: KeyboardEvent) => {if (event.key === 'Escape') {setOpen(false); trigger.current?.focus();}};
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape);};
  }, [open]);

  function markRead(ids: string[]) {
    setReadIds(current => {
      const next = [...new Set([...current, ...ids])].slice(-200);
      try {localStorage.setItem(storageKey, JSON.stringify(next));} catch { /* Reading still works when storage is unavailable. */ }
      return next;
    });
  }
  const groups = groupNotifications(events);
  const unread = groups.filter(group => group.ids.some(id => !readIds.includes(id))).length;
  return <div className="camera-notifications" ref={root} onBlur={event => {if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node)) setOpen(false);}}>
    <button ref={trigger} type="button" className="notification-trigger" aria-label={`Thông báo camera${unread ? `, ${unread} chưa đọc` : ''}`} aria-expanded={open} aria-controls="camera-notification-panel" onClick={() => setOpen(value => !value)}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4 M12 2V1"/></svg>
      {unread > 0 && <span className="notification-badge" aria-hidden="true">{unread}</span>}
    </button>
    {open && <section id="camera-notification-panel" className="notification-panel" aria-label="Sự kiện camera">
      <div className="notification-heading"><h2>Sự kiện camera</h2><button type="button" disabled={!unread} onClick={() => markRead(events.map(event => event.id).reverse())}>Đọc tất cả</button></div>
      <p className="field-hint">50 sự kiện gần nhất · gom cùng camera và loại trong 30 giây</p>
      {loading && <p role="status">Đang tải thông báo…</p>}
      {error && <p role="alert">{error} {events.length > 0 && 'Đang hiển thị dữ liệu lần tải trước.'}</p>}
      {!loading && !error && !events.length && <p>Chưa có sự kiện camera.</p>}
      <ul className="notification-list">{groups.map(({event, ids}) => <li key={event.id} className={ids.every(id => readIds.includes(id)) ? '' : 'is-unread'}>
        <a className="notification-event-link" href={`#${event.kind === 'UNKNOWN_ALERT' ? 'alerts' : 'history'}?event=${encodeURIComponent(event.id)}`} onClick={() => {markRead(ids); setOpen(false);}}><strong>{event.kind === 'UNKNOWN_ALERT' ? 'Cảnh báo người lạ' : 'Khuôn mặt mới vào ROI'}</strong>
        <p>{event.camera_name} · <time dateTime={event.recognized_at}>{new Date(event.recognized_at).toLocaleString('vi-VN', {timeZone: 'Asia/Ho_Chi_Minh'})}</time></p>
        <span>{ids.length > 1 && <span className="notification-group-count">{ids.length} sự kiện · </span>}{event.kind === 'UNKNOWN_ALERT' ? 'Xem evidence người lạ →' : 'Xem sự kiện →'}</span></a>
        <div className="notification-actions">
          {ids.some(id => !readIds.includes(id)) && <button type="button" onClick={() => markRead(ids)}>Đánh dấu đã đọc<span className="sr-only"> {event.camera_name}</span></button>}
        </div>
      </li>)}</ul>
      <a className="notification-footer" href="#alerts" onClick={() => setOpen(false)}>Mở báo cáo evidence người lạ →</a>
    </section>}
  </div>;
}

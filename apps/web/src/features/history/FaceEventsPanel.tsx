import {useEffect, useRef, useState} from 'react';
import {apiFetch} from '../../api/client';
import type {FacePresenceEvent} from '../../api/simpleRecognition';
import {downloadEvidenceReport} from './evidenceReport';
import {EvidenceMedia, evidenceLabels} from './EvidenceMedia';
import {DataState} from '../../ui/DataState';
import {Icon} from '../../ui/Icon';

export function FaceEventsPanel({cameraId, kind, compact = false, start, end, report = false, eventId}: {cameraId?: string; kind?: FacePresenceEvent['kind']; compact?: boolean; start?: string; end?: string; report?: boolean; eventId?: string}) {
  const [events, setEvents] = useState<FacePresenceEvent[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(() => {
    if (compact || eventId) return 0;
    const value = Number(new URLSearchParams(window.location.hash.split('?')[1]).get('offset') ?? 0);
    return Number.isInteger(value) && value >= 0 && value <= 1000000 && value % 50 === 0 ? value : 0;
  });
  const filterKey = JSON.stringify([cameraId, kind, start, end]);
  const previousFilter = useRef(filterKey);
  const selectedEvent = useRef<HTMLElement>(null);
  const focusedId = useRef<string | undefined>(undefined);
  const restoredScroll = useRef(false);
  function rememberScroll() {
    try { sessionStorage.setItem(`event-list-scroll:${window.location.hash}`, String(window.scrollY)); } catch { /* Optional browser preference. */ }
  }
  useEffect(() => {
    if (compact || eventId || loading || error || restoredScroll.current) return;
    restoredScroll.current = true;
    try {
      const key = `event-list-scroll:${window.location.hash}`;
      const saved = sessionStorage.getItem(key);
      if (saved !== null && Number.isFinite(Number(saved))) {
        window.scrollTo({ top: Math.max(0, Number(saved)), behavior: 'instant' });
        sessionStorage.removeItem(key);
      }
    } catch { /* The list still works without storage. */ }
  }, [compact, eventId, loading, error]);
  function detailsHref(event: FacePresenceEvent) {
    const params = new URLSearchParams(report || window.location.hash.startsWith('#history') ? window.location.hash.split('?')[1] : '');
    params.set('event', event.id);
    return `#${event.kind === 'UNKNOWN_ALERT' ? 'alerts' : 'history'}?${params}`;
  }
  useEffect(() => {
    if (!eventId || !events.some(event => event.id === eventId) || focusedId.current === eventId) return;
    selectedEvent.current?.focus();
    selectedEvent.current?.scrollIntoView?.({block: 'center'});
    focusedId.current = eventId;
  }, [eventId, events]);
  useEffect(() => {
    if (previousFilter.current !== filterKey) { previousFilter.current = filterKey; setOffset(0); }
  }, [filterKey]);
  useEffect(() => {
    if (compact || eventId) return;
    const [page, query] = window.location.hash.split('?');
    if (page !== '#alerts' && page !== '#history') return;
    const params = new URLSearchParams(query);
    if (offset) params.set('offset', String(offset)); else params.delete('offset');
    window.history.replaceState(null, '', `${page}${params.size ? `?${params}` : ''}`);
  }, [offset, compact, eventId]);
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    setLoading(true);
    setEvents([]);
    async function load() {
      if (document.visibilityState === 'hidden') {timer = setTimeout(() => void load(), 3000); return;}
      try {
        const params = new URLSearchParams();
        if (eventId) params.set('event_id', eventId);
        if (cameraId) params.set('camera_id', cameraId);
        if (kind) params.set('kind', kind);
        if (start) params.set('start', start);
        if (end) params.set('end', end);
        if (!compact) {params.set('offset', String(offset)); params.set('limit', '50');}
        const query = params.size ? `?${params}` : '';
        const response = await apiFetch(`/api/v1/recognition/face-events${query}`, {
          signal: controller.signal, cache: 'no-store'
        });
        if (!response.ok) throw new Error('Không tải được ảnh vào và cảnh báo.');
        const rows: FacePresenceEvent[] = await response.json();
        if (!disposed) {setEvents(rows); setError('');}
      } catch (reason) {
        if (!disposed) setError(reason instanceof Error ? reason.message : 'Không tải được cảnh báo.');
      } finally {
        if (!disposed) {setLoading(false); timer = setTimeout(() => void load(), 3000);}
      }
    }
    void load();
    return () => {disposed = true; controller.abort(); clearTimeout(timer);};
  }, [cameraId, kind, start, end, compact, offset, eventId]);
  return <section className={`event-workspace ${eventId ? 'event-detail-workspace' : ''}`} aria-label={report ? 'Báo cáo evidence người lạ' : 'Ảnh vào và cảnh báo người lạ'}>
    {!compact && !eventId && <div className="event-list-heading"><div><h2>{report ? 'Ảnh minh chứng' : 'Sự kiện đã ghi nhận'}</h2><p>{loading ? 'Đang cập nhật danh sách' : `${events.length} sự kiện trên trang này`} · Theo giờ Việt Nam</p></div>
      {report && <button className="secondary-button" type="button" disabled={loading || !!error || !events.length} onClick={() => downloadEvidenceReport(events, offset / 50 + 1)}><Icon name="download"/>Xuất báo cáo trang này (CSV)</button>}</div>}
    {error && <DataState error title={error} description={events.length ? 'Đang hiển thị dữ liệu lần tải trước. Hệ thống sẽ tự thử kết nối lại.' : 'Hệ thống sẽ tự thử kết nối lại.'}/>}
    {loading && <DataState loading title="Đang tải ảnh và cảnh báo…"/>}
    {!loading && !error && events.length === 0 && <DataState title={eventId ? 'Không tìm thấy sự kiện này hoặc sự kiện không còn khả dụng.' : report ? 'Chưa có evidence người lạ trong bộ lọc đã chọn.' : 'Chưa có ảnh vào hoặc cảnh báo.'} description={eventId ? 'Quay về danh sách để xem các sự kiện còn khả dụng.' : 'Sự kiện sẽ xuất hiện tại đây khi được camera ghi nhận.'}/>}
    <div className="evidence-list">{(compact ? events.slice(0, 8) : events).map(event => <article ref={event.id === eventId ? selectedEvent : undefined} tabIndex={event.id === eventId ? -1 : undefined} aria-label={event.id === eventId ? 'Sự kiện đang xem' : undefined} className={`evidence-row ${event.id === eventId ? 'selected-event' : ''}`} key={event.id}>
      <EvidenceMedia event={event}/>
      <div className="evidence-copy">
        <div className="evidence-row-title"><span className={`product-badge ${event.kind === 'UNKNOWN_ALERT' ? 'tone-warning' : 'tone-neutral'}`}><Icon name={event.kind === 'UNKNOWN_ALERT' ? 'warning' : 'camera'}/>{event.kind === 'UNKNOWN_ALERT' ? 'Người lạ' : 'Ảnh vào ROI'}</span><span className={`product-badge state-evidence-${event.evidence_status.toLowerCase()}`}>{evidenceLabels[event.evidence_status]}</span></div>
        <h3>{event.kind === 'UNKNOWN_ALERT' ? 'Cảnh báo người lạ' : 'Khuôn mặt mới vào ROI'}</h3>
        <p className="evidence-camera"><Icon name="camera"/>{event.camera_name}</p>
        <time dateTime={event.recognized_at}>{new Date(event.recognized_at).toLocaleString('vi-VN', {timeZone: 'Asia/Ho_Chi_Minh'})}</time>
        {eventId && <div className="event-facts"><span>Căn cứ ghi nhận</span><p>{event.kind === 'UNKNOWN_ALERT' ? `${event.consecutive_unknown} frame liên tiếp không khớp ảnh đăng ký.` : 'Khuôn mặt mới xuất hiện trong vùng theo dõi.'}</p><span>Trạng thái ảnh</span><p>{evidenceLabels[event.evidence_status]}</p></div>}
        {!eventId && event.kind === 'UNKNOWN_ALERT' && <p className="event-basis">{event.consecutive_unknown} frame liên tiếp không khớp ảnh đăng ký.</p>}
        <div className="evidence-actions">{!eventId && <a className="event-detail-link" href={detailsHref(event)} onClick={rememberScroll}>Xem chi tiết <Icon name="arrow"/></a>}
          {event.evidence_status === 'READY' && event.evidence_key && <a className={eventId ? 'button-link' : 'evidence-original-link'} href={`/api/v1/recognition/evidence/${encodeURIComponent(event.evidence_key)}`} target="_blank" rel="noreferrer">Mở ảnh minh chứng</a>}</div>
      </div>
    </article>)}</div>
    {!compact && !eventId && <div className="pagination-bar"><span>Trang {offset / 50 + 1} <span className="pagination-note">· Tối đa 50 sự kiện</span></span><div><button disabled={loading || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 50))}>Trang trước</button><button disabled={loading || events.length < 50} onClick={() => setOffset(value => value + 50)}>Trang sau</button></div></div>}
  </section>;
}

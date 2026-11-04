import {FaceEventsPanel} from './FaceEventsPanel';

export function CameraEventDetails({eventId, page}: {eventId: string; page: 'alerts' | 'history'}) {
  const params = new URLSearchParams(window.location.hash.split('?')[1]);
  params.delete('event');
  const backHref = `#${page}${params.size ? `?${params}` : ''}`;
  return <section className="camera-event-details" aria-label="Chi tiết sự kiện camera">
    <div className="event-detail-navigation"><a href={backHref}>← {page === 'alerts' ? 'Về báo cáo evidence người lạ' : 'Về lịch sử'}</a><span>Chi tiết sự kiện · Giờ Việt Nam</span></div>
    <FaceEventsPanel eventId={eventId} kind={page === 'alerts' ? 'UNKNOWN_ALERT' : undefined}/>
  </section>;
}

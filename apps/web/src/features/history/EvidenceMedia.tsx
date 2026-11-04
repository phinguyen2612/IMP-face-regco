import {useEffect, useState} from 'react';
import type {FacePresenceEvent} from '../../api/simpleRecognition';
import {Icon} from '../../ui/Icon';

export const evidenceLabels = {PENDING: 'Đang lưu ảnh', READY: 'Có ảnh minh chứng', FAILED: 'Lưu ảnh thất bại', EXPIRED: 'Ảnh đã hết hạn'};
export function EvidenceMedia({event}: {event: FacePresenceEvent}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [event.evidence_key]);
  const message = failed ? 'Không tải được ảnh minh chứng.' : event.evidence_status === 'PENDING' ? 'Đang lưu ảnh…' : event.evidence_status === 'EXPIRED' ? 'Ảnh đã hết hạn lưu.' : 'Không lưu được ảnh; sự kiện vẫn được ghi nhận.';
  return <div className={`evidence-media ${event.evidence_status.toLowerCase()}`}>
    {event.evidence_status === 'READY' && event.evidence_key && !failed
      ? <img src={`/api/v1/recognition/evidence/${encodeURIComponent(event.evidence_key)}`} alt={event.kind === 'UNKNOWN_ALERT' ? 'Snapshot cảnh báo người lạ' : 'Khuôn mặt khi vào ROI'} loading="lazy" onError={() => setFailed(true)}/>
      : <div className="evidence-placeholder"><Icon name={event.evidence_status === 'PENDING' ? 'clock' : 'image'}/><p>{message}</p>{failed && <button type="button" onClick={() => setFailed(false)}>Tải lại ảnh</button>}</div>}
  </div>;
}

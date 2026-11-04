import type {FacePresenceEvent} from '../../api/simpleRecognition';

const evidenceLabels = {PENDING: 'Đang lưu ảnh', READY: 'Có ảnh minh chứng', FAILED: 'Không lưu được ảnh', EXPIRED: 'Ảnh đã hết hạn'};

export function evidenceReportCsv(events: FacePresenceEvent[]): string {
  const cell = (value: string | number) => {
    const text = String(value);
    const safe = /^[\s]*[=+@-]/.test(text) ? `'${text}` : text;
    return `"${safe.replaceAll('"', '""')}"`;
  };
  return '\uFEFF' + [
    ['Mã sự kiện', 'Camera', 'Thời gian (Việt Nam)', 'Số frame liên tiếp', 'Trạng thái evidence'],
    ...events.filter(event => event.kind === 'UNKNOWN_ALERT').map(event => [event.id, event.camera_name,
      new Date(event.recognized_at).toLocaleString('vi-VN', {timeZone: 'Asia/Ho_Chi_Minh'}),
      event.consecutive_unknown, evidenceLabels[event.evidence_status]])
  ].map(row => row.map(cell).join(',')).join('\r\n');
}

export function downloadEvidenceReport(events: FacePresenceEvent[], page: number) {
  const url = URL.createObjectURL(new Blob([evidenceReportCsv(events)], {type: 'text/csv;charset=utf-8'}));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `evidence-nguoi-la-trang-${page}.csv`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

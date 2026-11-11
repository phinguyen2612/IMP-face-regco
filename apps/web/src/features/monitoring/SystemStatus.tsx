import type { RuntimeStatus } from '../../api/contracts';
import { DataState } from '../../ui/DataState';
import { StatusBadge } from '../../ui/StatusBadge';
import { formatDateTime } from '../../ui/format';

export function SystemStatus({ statuses }: { statuses: RuntimeStatus[] }) {
  return <section className="system-workspace" aria-labelledby="runtime-heading">
    <div className="usability-guide"><strong>Báo cáo từ worker</strong><span>Trạng thái dưới đây theo lần báo cáo gần nhất. Kiểm tra thời điểm hình mới để đánh giá độ cập nhật.</span></div>
    <h2 id="runtime-heading">Hoạt động của worker</h2>
    {!statuses.length ? <DataState title="Chưa nhận được trạng thái" description="Trạng thái sẽ xuất hiện khi worker gửi báo cáo. Mở Giám sát để kiểm tra nguồn hình." /> : <div className="grid">{statuses.map(runtime => <article key={`${runtime.worker_id}:${runtime.camera_id}`}>
      <StatusBadge tone={runtime.worker_health === 'unhealthy' ? 'danger' : runtime.worker_health === 'degraded' ? 'warning' : 'neutral'}>{runtime.worker_health === 'healthy' ? 'Worker báo cáo bình thường' : runtime.worker_health === 'degraded' ? 'Worker cần chú ý' : 'Worker báo cáo lỗi'}</StatusBadge>
      <h3>Camera đang báo cáo</h3><p className="field-hint">Hình gần nhất: {formatDateTime(runtime.last_frame_at)}</p>
      <dl><dt>Kết nối camera</dt><dd>{runtime.camera_state}</dd><dt>FPS nguồn hình</dt><dd>{runtime.input_fps.toFixed(1)}</dd><dt>FPS xử lý</dt><dd>{runtime.processed_fps.toFixed(1)}</dd><dt>Frame bị bỏ</dt><dd>{runtime.dropped_frames}</dd><dt>Track đang theo dõi</dt><dd>{runtime.active_tracks}</dd><dt>Bộ đệm</dt><dd>{runtime.ring_buffer_frames} / {runtime.ring_buffer_capacity}</dd></dl>
      {runtime.error_category && <p className="field-hint">{runtime.error_category === 'PERSON_DETECTOR_NOT_CONFIGURED' ? 'Đang cấp hình cho bộ so sánh khuôn mặt.' : `Cần kiểm tra: ${runtime.error_category}`}</p>}
      <details className="runtime-details"><summary>Thông tin kỹ thuật</summary><p>Camera: {runtime.camera_id}</p><p>Worker: {runtime.worker_id}</p><p>Phiên bản cấu hình: {runtime.active_config_revision ?? 'Chưa có'}</p></details>
    </article>)}</div>}
    <p><a className="quiet-action" href="#monitoring">Mở giám sát camera →</a></p>
  </section>;
}

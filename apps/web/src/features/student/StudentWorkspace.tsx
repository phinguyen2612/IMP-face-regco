import { useEffect, useRef, useState } from 'react';
import { getMyProfile, listMyAttendance, listMyEvents, listMyFaceImages, loadPrivateImage, myEventEvidenceUrl, myFaceImageUrl, uploadMyFaceImages, type StudentAttendance, type StudentEvent, type StudentProfile } from '../../api/student';
import type { FaceImagePublic, UploadResult } from '../../api/registry';
import type { WorkspacePage } from '../../app/Sidebar';
import { DataState } from '../../ui/DataState';
import { StatusBadge } from '../../ui/StatusBadge';
import { formatDateTime } from '../../ui/format';

export function StudentWorkspace({ page }: { page: WorkspacePage }) {
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [images, setImages] = useState<FaceImagePublic[]>([]);
  const [attendance, setAttendance] = useState<StudentAttendance[]>([]);
  const [events, setEvents] = useState<StudentEvent[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult[] | null>(null);
  const uploading = useRef(false);

  useEffect(() => {
    let alive = true;
    setLoading(true); setError('');
    const load = page === 'me/profile' ? getMyProfile().then(v => { if (alive) setProfile(v); })
      : page === 'me/enrollment' ? listMyFaceImages().then(v => { if (alive) setImages(v); })
      : page === 'me/attendance' ? listMyAttendance().then(v => { if (alive) setAttendance(v); })
      : listMyEvents().then(v => { if (alive) setEvents(v); });
    load.catch(e => { if (alive) setError(e instanceof Error ? e.message : 'Không tải được dữ liệu'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [page, retry]);

  async function upload(files: FileList | null) {
    if (!files?.length || uploading.current) return;
    uploading.current = true; setBusy(true); setError(''); setResult(null);
    try { setResult(await uploadMyFaceImages(Array.from(files))); setImages(await listMyFaceImages()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Tải ảnh thất bại'); }
    finally { uploading.current = false; setBusy(false); }
  }

  return <section className="role-workspace">
    {error && <><DataState error title={error} /><button type="button" onClick={() => setRetry(v => v + 1)}>Thử tải lại</button></>}
    {loading ? <DataState loading title="Đang tải thông tin của bạn…" /> : <>
      {page === 'me/profile' && profile && <article className="workspace-card">
        <div className="profile-summary"><span className="profile-avatar" aria-hidden="true">{profile.full_name.trim().split(/\s+/).slice(-2).map(word => word[0]).join('')}</span>
          <div><p className="eyebrow">THÔNG TIN SINH VIÊN</p><h2 className="student-name">{profile.full_name}</h2><p>Mã sinh viên: {profile.student_id ?? 'Chưa liên kết'}</p>
            <StatusBadge tone={profile.recognition_ready ? 'success' : 'warning'}>{profile.recognition_ready ? 'Đã sẵn sàng đối chiếu' : 'Chưa có ảnh được duyệt để đối chiếu'}</StatusBadge></div></div>
        <div className="profile-actions"><a className="quiet-action" href="#me/enrollment">Quản lý ảnh đăng ký →</a><a className="quiet-action" href="#me/attendance">Xem điểm danh →</a></div>
      </article>}
      {page === 'me/enrollment' && <>
        <article className="workspace-card"><p className="eyebrow">ẢNH ĐĂNG KÝ</p><h2>Đăng ký khuôn mặt</h2><p>Chụp chính diện, đủ sáng, mỗi ảnh chỉ có một khuôn mặt. Ảnh mới chờ duyệt; chỉ ảnh được duyệt mới có thể dùng để đối chiếu.</p>
          <label className="enrollment-upload">{busy ? 'Đang tải ảnh…' : 'Chọn ảnh để đăng ký'}<input aria-label="Chọn ảnh khuôn mặt" type="file" accept="image/jpeg,image/png" multiple disabled={busy} onChange={e => { void upload(e.currentTarget.files); e.currentTarget.value = ''; }} /><span className="field-hint">Ảnh JPEG hoặc PNG · Có thể chọn nhiều ảnh</span></label>
          {result && <div role="status" className="upload-results">{result.map((item, index) => <p key={`${item.filename}-${index}`}>{item.filename}: {item.status === 'STORED_PENDING' ? 'Đang chờ duyệt' : item.error_category ?? 'Không tải được'}</p>)}</div>}
        </article>
        {images.length === 0 ? !error && <DataState title="Chưa có ảnh đăng ký" description="Chọn ảnh ở phía trên để gửi duyệt khuôn mặt của bạn." /> : <div className="student-image-grid">{images.map(image => <article className="workspace-card" key={image.id}>
          <img src={myFaceImageUrl(image.id)} alt={`Ảnh đăng ký ${image.original_filename}`} loading="lazy" /><h3>{image.original_filename}</h3>
          <StatusBadge tone={image.review_state === 'APPROVED' ? 'success' : image.review_state === 'REJECTED' ? 'danger' : 'warning'}>{image.review_state === 'APPROVED' ? 'Đã duyệt' : image.review_state === 'REJECTED' ? 'Từ chối' : 'Chờ duyệt'}</StatusBadge>
        </article>)}</div>}
      </>}
      {page === 'me/attendance' && <article className="workspace-card"><h2>Điểm danh của tôi</h2><p className="field-hint">Lượt ghi nhận theo ngày · Thời gian hiển thị theo giờ Việt Nam</p>
        {attendance.length === 0 ? !error && <DataState title="Chưa có lượt điểm danh" description="Lượt điểm danh sẽ xuất hiện sau khi hệ thống xác minh danh tính của bạn." /> : <div className="table-wrap" tabIndex={0} aria-label="Bảng điểm danh cá nhân"><table><thead><tr><th>Ngày</th><th>Camera</th><th>Lần đầu</th><th>Lần cuối</th><th>Trạng thái</th></tr></thead><tbody>{attendance.map(row => <tr key={row.id}><td>{row.attendance_date}</td><td>{row.camera_name ?? '—'}</td><td>{formatDateTime(row.first_seen_at)}</td><td>{formatDateTime(row.last_seen_at)}</td><td><StatusBadge tone="success">Đã ghi nhận</StatusBadge></td></tr>)}</tbody></table></div>}
      </article>}
      {page === 'me/history' && <article className="workspace-card"><h2>Lịch sử nhận diện</h2><p className="field-hint">Các sự kiện nhận diện thuộc hồ sơ của bạn · Giờ Việt Nam</p>
        {events.length === 0 ? !error && <DataState title="Chưa có lịch sử nhận diện" description="Sự kiện và ảnh minh chứng sẽ xuất hiện khi có lượt ghi nhận." /> : <div className="table-wrap" tabIndex={0} aria-label="Bảng lịch sử cá nhân"><table><thead><tr><th>Thời điểm</th><th>Camera</th><th>Minh chứng</th></tr></thead><tbody>{events.map(event => <tr key={event.id}><td>{formatDateTime(event.recognized_at)}</td><td>{event.camera_name ?? '—'}</td><td><EvidenceLink url={myEventEvidenceUrl(event.id)} /></td></tr>)}</tbody></table></div>}
      </article>}
    </>}
  </section>;
}

function EvidenceLink({ url }: { url: string }) {
  const [src, setSrc] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => () => { if (src) URL.revokeObjectURL(src); }, [src]);
  async function load() {
    setBusy(true); setError('');
    try { const next = await loadPrivateImage(url); if (mounted.current) setSrc(next); else URL.revokeObjectURL(next); }
    catch { if (mounted.current) setError('Không tải được ảnh minh chứng'); }
    finally { if (mounted.current) setBusy(false); }
  }
  return src ? <a href={src} target="_blank" rel="noreferrer">Mở ảnh minh chứng</a> : <><button type="button" disabled={busy} onClick={() => void load()}>{busy ? 'Đang tải…' : 'Xem minh chứng'}</button>{error && <span role="alert">{error}</span>}</>;
}

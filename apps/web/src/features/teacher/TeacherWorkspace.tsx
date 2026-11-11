import { useEffect, useRef, useState } from 'react';
import { createTeacherSession, completeTeacherSession, getSessionAttendance, listPendingFaceReviews, listTeacherCameras, listTeacherClasses, listTeacherSessions, reviewFaceImage, type AttendanceEntry, type Classroom, type ClassSession, type FaceReviewImage, type TeacherCamera } from '../../api/classes';
import type { WorkspacePage } from '../../app/Sidebar';
import { DataState } from '../../ui/DataState';
import { StatusBadge } from '../../ui/StatusBadge';
import { formatDateTime, localDateTimeWithOffset } from '../../ui/format';

export function TeacherWorkspace({ page }: { page: WorkspacePage }) {
  const [classes, setClasses] = useState<Classroom[]>([]);
  const [selected, setSelected] = useState('');
  const [sessions, setSessions] = useState<ClassSession[]>([]);
  const [report, setReport] = useState<{ label: string; items: AttendanceEntry[] } | null>(null);
  const [reviews, setReviews] = useState<FaceReviewImage[]>([]);
  const [cameras, setCameras] = useState<TeacherCamera[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [retry, setRetry] = useState(0);
  const reportRequest = useRef(0);
  const submitting = useRef(false);

  useEffect(() => {
    let alive = true;
    setLoading(true); setError('');
    const load = page === 'teacher/review' ? listPendingFaceReviews().then(items => { if (alive) setReviews(items); })
      : listTeacherClasses().then(items => { if (alive) { setClasses(items); setSelected(current => items.some(item => item.id === current) ? current : items[0]?.id ?? ''); } });
    load.catch(e => { if (alive) setError(e instanceof Error ? e.message : 'Không tải được dữ liệu'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; reportRequest.current++; };
  }, [page, retry]);

  useEffect(() => {
    reportRequest.current++; setReport(null); setReportLoading(false); setSessions([]); setCameras([]);
    if (!selected || page !== 'teacher/classes') return;
    let alive = true;
    setSessionsLoading(true); setError('');
    Promise.all([listTeacherSessions(selected), listTeacherCameras()]).then(([s, c]) => {
      if (alive) { setSessions(s); setCameras(c); }
    }).catch(e => { if (alive) setError(e instanceof Error ? e.message : 'Không tải được lớp'); })
      .finally(() => { if (alive) setSessionsLoading(false); });
    return () => { alive = false; reportRequest.current++; };
  }, [selected, page, retry]);

  async function showAttendance(session: ClassSession) {
    const request = ++reportRequest.current;
    setReportLoading(true); setReport(null); setError('');
    try { const next = await getSessionAttendance(session.classroom_id, session.id); if (request === reportRequest.current) setReport({ label: session.label, items: next.items }); }
    catch (e) { if (request === reportRequest.current) setError(e instanceof Error ? e.message : 'Không tải được điểm danh'); }
    finally { if (request === reportRequest.current) setReportLoading(false); }
  }

  async function createSession(form: HTMLFormElement) {
    if (submitting.current) return;
    const data = new FormData(form);
    const startsAt = new Date(String(data.get('starts_at')));
    const endsAt = new Date(String(data.get('ends_at')));
    if (!(endsAt > startsAt)) { setError('Thời gian kết thúc phải sau thời gian bắt đầu.'); return; }
    submitting.current = true; setBusy(true); setError(''); setMessage('');
    try {
      await createTeacherSession(selected, { camera_id: String(data.get('camera_id')), label: String(data.get('label')), starts_at: localDateTimeWithOffset(String(data.get('starts_at'))), ends_at: localDateTimeWithOffset(String(data.get('ends_at'))), timezone_id: Intl.DateTimeFormat().resolvedOptions().timeZone });
      setSessions(await listTeacherSessions(selected)); setMessage('Đã tạo buổi học.'); form.reset();
    } catch (e) { setError(e instanceof Error ? e.message : 'Không tạo được buổi học'); }
    finally { submitting.current = false; setBusy(false); }
  }

  async function review(image: FaceReviewImage, decision: 'APPROVE' | 'REJECT') {
    if (submitting.current || (decision === 'REJECT' && !window.confirm(`Từ chối ảnh ${image.original_filename}?`))) return;
    submitting.current = true; setBusy(true); setError(''); setMessage('');
    try { await reviewFaceImage(image.id, decision); setReviews(current => current.filter(item => item.id !== image.id)); setMessage(decision === 'APPROVE' ? 'Đã duyệt ảnh đăng ký.' : 'Đã từ chối ảnh đăng ký.'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Không lưu được quyết định'); }
    finally { submitting.current = false; setBusy(false); }
  }

  async function complete(session: ClassSession) {
    if (submitting.current || !window.confirm(`Hoàn tất buổi “${session.label}”? Buổi học sẽ chuyển sang trạng thái hoàn tất.`)) return;
    submitting.current = true; setBusy(true); setError('');
    try { await completeTeacherSession(session.classroom_id, session.id); setSessions(await listTeacherSessions(selected)); setMessage('Đã hoàn tất buổi học.'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Không hoàn tất được buổi học'); }
    finally { submitting.current = false; setBusy(false); }
  }

  return <section className="role-workspace">
    {error && <><DataState error title={error} /><button type="button" disabled={busy} onClick={() => setRetry(v => v + 1)}>Thử tải lại</button></>}
    {message && <p role="status">{message}</p>}
    {loading ? <DataState loading title="Đang tải không gian giảng dạy…" /> : page === 'teacher/review' ? <>
      <div className="usability-guide"><strong>Ảnh đăng ký chờ duyệt</strong><span>Kiểm tra đúng sinh viên, một khuôn mặt rõ và đủ sáng trước khi duyệt.</span></div>
      {reviews.length === 0 ? !error && <DataState title="Không có ảnh chờ duyệt" description="Ảnh mới của sinh viên thuộc lớp bạn phụ trách sẽ xuất hiện tại đây." /> : reviews.map(image => <article className="workspace-card review-card" key={image.id}>
        <img src={image.content_url} alt={`Ảnh chờ duyệt ${image.original_filename}`} loading="lazy" /><div><StatusBadge tone="warning">Chờ duyệt</StatusBadge><h3>{image.original_filename}</h3><p>{image.width} × {image.height} · {image.source}</p>
          <button className="button-primary" disabled={busy} onClick={() => void review(image, 'APPROVE')}>Duyệt ảnh</button><button className="danger-button" disabled={busy} onClick={() => void review(image, 'REJECT')}>Từ chối</button></div>
      </article>)}
    </> : !classes.length ? !error && <DataState title="Chưa có lớp được phân công" description="Lớp học sẽ xuất hiện sau khi quản trị viên phân công bạn phụ trách." /> : <>
      <div className="filter-surface"><label>Lớp của tôi<select disabled={busy} value={selected} onChange={e => setSelected(e.target.value)}>{classes.map(c => <option key={c.id} value={c.id}>{c.name} · {c.course} {c.section}</option>)}</select></label></div>
      {sessionsLoading ? <DataState loading title="Đang tải buổi học…" /> : <>
        <details className="creation-panel"><summary>+ Tạo buổi điểm danh</summary><article className="workspace-card"><h2>Tạo buổi điểm danh</h2><p className="field-hint">Nhập thời gian theo múi giờ của thiết bị. Kiểm tra thời điểm trước khi tạo buổi.</p>
          <form className="form-grid" onSubmit={e => { e.preventDefault(); void createSession(e.currentTarget); }}><label>Tên buổi<input name="label" required /></label><label>Camera<select name="camera_id" required><option value="">Chọn camera</option>{cameras.map(camera => <option key={camera.id} value={camera.id}>{camera.name}</option>)}</select></label><label>Bắt đầu<input name="starts_at" type="datetime-local" required /></label><label>Kết thúc<input name="ends_at" type="datetime-local" required /></label><button type="submit" disabled={busy || !selected || !cameras.length}>{busy ? 'Đang lưu…' : 'Tạo buổi'}</button></form>
          {!cameras.length && <p className="field-hint">Chưa có camera khả dụng để tạo buổi. Liên hệ quản trị viên để kiểm tra nguồn hình.</p>}
        </article></details>
        <h2>Buổi học</h2>
        {!sessions.length && !error && <DataState title="Chưa có buổi điểm danh" description="Tạo buổi đầu tiên để theo dõi điểm danh của lớp đã chọn." />}
        {sessions.map(session => <article className="workspace-card session-row" key={session.id}><div><h3>{session.label}</h3><p>{formatDateTime(session.starts_at)} · {session.state}</p></div><button disabled={busy || reportLoading} onClick={() => void showAttendance(session)}>Xem điểm danh</button>{!session.done && <button disabled={busy} onClick={() => void complete(session)}>Hoàn tất</button>}</article>)}
        {reportLoading && <DataState loading title="Đang tải kết quả điểm danh…" />}
        {report && <AttendanceTable label={report.label} items={report.items} />}
      </>}
    </>}
  </section>;
}

function AttendanceTable({ label, items }: { label: string; items: AttendanceEntry[] }) {
  return <article className="workspace-card"><p className="eyebrow">KẾT QUẢ ĐIỂM DANH</p><h2>{label}</h2>{!items.length ? <DataState title="Buổi học chưa có dữ liệu điểm danh" /> : <div className="table-wrap" tabIndex={0} aria-label="Kết quả điểm danh buổi học"><table><thead><tr><th>Sinh viên</th><th>Mã</th><th>Trạng thái</th><th>Thời điểm</th><th>Camera</th></tr></thead><tbody>{items.map((item, index) => <tr key={`${item.person_id}-${index}`}><td>{item.full_name}</td><td>{item.student_id ?? '—'}</td><td><StatusBadge>{item.status}</StatusBadge></td><td>{formatDateTime(item.recognized_at)}</td><td>{item.camera_id ?? '—'}</td></tr>)}</tbody></table></div>}</article>;
}

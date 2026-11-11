import {useEffect, useState} from 'react';
import {FaceEventsPanel} from './FaceEventsPanel';
import {listCameras} from '../../api/client';
import {apiFetch} from '../../api/client';
import type {CameraPublic} from '../../api/contracts';
import {DataState} from '../../ui/DataState';
import {PersonPicker} from '../../ui/PersonPicker';

type EventRow = {id:string;camera_id:string;camera_name:string;track_id:number|null;person_id:string;full_name:string;student_id:string|null;recognized_at:string;attendance_date:string;evidence_key:string|null};
type AttendanceRow = {id:string;attendance_date:string;person_id:string;full_name:string;student_id:string|null;first_seen_at:string;last_seen_at:string;exited_at:string|null;camera_id:string;camera_name:string};

export function RecognitionHistoryPanel() {
  const [tab,setTab]=useState<'events'|'attendance'|'faces'>(()=>{const value=new URLSearchParams(window.location.hash.split('?')[1]).get('tab');return value==='faces'||value==='attendance'?value:'events';});
  const [events,setEvents]=useState<EventRow[]>([]); const [attendance,setAttendance]=useState<AttendanceRow[]>([]);
  const initialParam=(name:string)=>new URLSearchParams(window.location.hash.split('?')[1]).get(name)??'';
  const [cameras,setCameras]=useState<CameraPublic[]>([]); const [camera,setCamera]=useState(()=>initialParam('camera'));
  const [start,setStart]=useState(()=>initialParam('start')); const [end,setEnd]=useState(()=>initialParam('end')); const [person,setPerson]=useState(()=>initialParam('person'));
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);
  const invalidRange=tab!=='faces'&&!!start&&!!end&&start>end;
  useEffect(()=>{const query=new URLSearchParams(window.location.hash.split('?')[1]);for(const key of ['tab','camera','start','end','person'])query.delete(key);query.set('tab',tab);if(camera)query.set('camera',camera);if(start)query.set('start',start);if(end)query.set('end',end);if(person)query.set('person',person);window.history.replaceState(null,'',`#history?${query}`);},[tab,camera,start,end,person]);
  const query=new URLSearchParams(); if(start)query.set('start',start); if(end)query.set('end',end); if(camera)query.set('camera_id',camera); if(person)query.set('person_id',person);
  const params=query.toString();
  useEffect(()=>{void listCameras().then(setCameras).catch(()=>undefined);},[]);
  useEffect(() => {
    if (tab === 'faces' || invalidRange) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setEvents([]); setAttendance([]); setError(''); setLoading(true);
    async function load() {
      try {
        const endpoint = tab === 'events' ? '/api/v1/recognition/events' : '/api/v1/attendance';
        const response = await apiFetch(`${endpoint}?${params}`, {cache: 'no-store', signal: controller.signal});
        if (!response.ok) throw new Error('Không tải được lịch sử.');
        const rows = await response.json();
        if (!controller.signal.aborted) {if (tab === 'events') setEvents(rows); else setAttendance(rows); setError('');}
      } catch (reason) {if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Không tải được lịch sử.');}
      finally {if (!controller.signal.aborted) {setLoading(false); timer = setTimeout(() => void load(), 5000);}}
    }
    void load();
    return () => {controller.abort(); clearTimeout(timer);};
  }, [params, tab, invalidRange]);
  return <section className="history-panel" aria-label="Lịch sử nhận diện và điểm danh">
    <div className="history-toolbar">
      <button type="button" aria-pressed={tab==='faces'} onClick={()=>setTab('faces')}>Ảnh vào &amp; cảnh báo</button>
      <button type="button" aria-pressed={tab==='events'} onClick={()=>setTab('events')}>Lịch sử xác minh</button>
      <button type="button" aria-pressed={tab==='attendance'} onClick={()=>setTab('attendance')}>Điểm danh</button>
      {tab==='attendance'&&!invalidRange&&<a className="button-link" href={`/api/v1/attendance/export.xlsx${params?`?${params}`:''}`}>Xuất Excel</a>}
    </div>
    <div className="history-filters">
      {tab !== 'faces' && <label>Từ ngày<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>}
      {tab !== 'faces' && <label>Đến ngày<input type="date" min={start} value={end} onChange={e=>setEnd(e.target.value)}/></label>}
      <label>Camera<select value={camera} onChange={e=>setCamera(e.target.value)}><option value="">Tất cả</option>{cameras.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      {tab !== 'faces' && <PersonPicker value={person} onChange={setPerson} label="Người cần tra cứu"/>}
    </div>
    {invalidRange&&<DataState error title="Ngày kết thúc phải từ ngày bắt đầu trở đi."/>}{error&&!invalidRange&&<DataState error title={error} description="Hệ thống đang thử kết nối lại. Dữ liệu còn hiển thị thuộc lần tải trước."/>}
    {invalidRange ? null : tab==='faces'?<FaceEventsPanel cameraId={camera||undefined}/>:tab==='events'?<div className="history-list">{loading?<DataState loading title="Đang tải lịch sử…"/>:events.length===0?!error&&<DataState title="Chưa có sự kiện xác minh phù hợp" description="Thử đổi ngày, camera hoặc người cần tra cứu."/>:events.map(row=><article key={row.id} className="history-event">
      {row.evidence_key?<img src={`/api/v1/recognition/evidence/${encodeURIComponent(row.evidence_key)}`} alt={`Ảnh minh chứng ${row.full_name}`} loading="lazy"/>:<div className="evidence-expired">Ảnh minh chứng đã hết hạn</div>}
      <div><h3>{row.full_name}</h3><p>{row.student_id||row.person_id}</p><p>{new Date(row.recognized_at).toLocaleString('vi-VN', {timeZone:'Asia/Ho_Chi_Minh'})} · {row.camera_name}</p><p>{row.track_id==null?'Không có Track ID':`Track #${row.track_id}`}</p></div>
    </article>)}</div>:<div className="table-scroll" tabIndex={0} aria-label="Bảng điểm danh"><table><thead><tr><th>Ngày</th><th>Mã</th><th>Họ tên</th><th>Vào</th><th>Ra</th><th>Camera</th></tr></thead><tbody>{attendance.map(row=><tr key={row.id}><td>{row.attendance_date}</td><td>{row.student_id||row.person_id}</td><td>{row.full_name}</td><td>{new Date(row.first_seen_at).toLocaleTimeString('vi-VN', {timeZone:'Asia/Ho_Chi_Minh'})}</td><td>{row.exited_at?new Date(row.exited_at).toLocaleTimeString('vi-VN', {timeZone:'Asia/Ho_Chi_Minh'}):'Đang có mặt'}</td><td>{row.camera_name}</td></tr>)}</tbody></table>{loading?<DataState loading title="Đang tải điểm danh…"/>:!error&&attendance.length===0&&<DataState title="Chưa có dữ liệu điểm danh trong bộ lọc"/>}</div>}
    {tab !== 'faces' && <p className="field-hint">Chỉ danh tính đã xác minh mới được ghi điểm danh. Điểm danh tự khử trùng theo người và ngày tại múi giờ Việt Nam; ảnh minh chứng tự xóa theo thời hạn camera.</p>}
  </section>;
}

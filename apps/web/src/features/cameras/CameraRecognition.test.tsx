import {cleanup, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {act} from '@testing-library/react';
import type {CameraPublic} from '../../api/contracts';
import {CameraRecognition} from './CameraRecognition';

afterEach(() => {cleanup(); vi.useRealTimers(); vi.unstubAllGlobals();});

it('keeps the same image element across processed frames', async () => {
  vi.useFakeTimers();
  let frame = 0;
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({state:'READY',
    frame_id:String(++frame), preview:`data:image/jpeg;base64,frame${frame}`,
    preview_remaining_ms:2500, faces:[]
  })));
  render(<CameraRecognition camera={{id:'cam',name:'Test',revision:'r1',lifecycle:'ACTIVE',enabled:true} as CameraPublic} />);
  await act(async () => {await vi.advanceTimersByTimeAsync(0);});
  const image = screen.getByRole('img');
  await act(async () => {await vi.advanceTimersByTimeAsync(250);});
  expect(screen.getByRole('img')).toBe(image);
  expect(image.getAttribute('src')).toContain('frame2');
});

it('keeps matching frame and boxes during busy replies without extending freshness', async () => {
  vi.useFakeTimers();
  let requests = 0;
  vi.stubGlobal('fetch', vi.fn(async () => Response.json(++requests === 1 ? {
    state:'READY',frame_id:'one',preview:'data:image/jpeg;base64,one',preview_remaining_ms:1000,
    faces:[{box:[.1,.2,.3,.4],state:'VERIFIED',full_name:'Test Person',similarity:.9}]
  } : {state:'RECOGNITION_BUSY',preview:'data:image/jpeg;base64,different',preview_remaining_ms:2500,faces:[]})));
  render(<CameraRecognition camera={{id:'cam',revision:'r1',lifecycle:'ACTIVE',enabled:true} as CameraPublic} />);
  await act(async () => {await vi.advanceTimersByTimeAsync(0);});
  const image = screen.getByRole('img');
  await act(async () => {await vi.advanceTimersByTimeAsync(800);});
  expect(screen.getByRole('img')).toBe(image);
  expect(image.getAttribute('src')).toBe('data:image/jpeg;base64,one');
  expect(screen.getByTestId('face-detection-box').textContent).toContain('Test Person');
  await act(async () => {await vi.advanceTimersByTimeAsync(250);});
  expect(screen.queryByRole('img')).toBeNull();
  expect(screen.queryByTestId('face-detection-box')).toBeNull();
});

it('clears the old frame when a busy reply belongs to a new stream session', async () => {
  vi.useFakeTimers();
  let requests = 0;
  vi.stubGlobal('fetch', vi.fn(async () => Response.json(++requests === 1 ? {
    state:'READY',stream_session_id:'old',preview:'data:image/jpeg;base64,old',preview_remaining_ms:2500,
    faces:[{box:[.1,.2,.3,.4],state:'VERIFIED',full_name:'Test Person',similarity:.9}]
  } : {state:'RECOGNITION_BUSY',stream_session_id:'new',faces:[]})));
  render(<CameraRecognition camera={{id:'cam',revision:'r1',lifecycle:'ACTIVE',enabled:true} as CameraPublic} />);
  await act(async () => {await vi.advanceTimersByTimeAsync(0);});
  expect(screen.getByTestId('face-detection-box')).toBeTruthy();
  await act(async () => {await vi.advanceTimersByTimeAsync(250);});
  expect(screen.queryByRole('img')).toBeNull();
  expect(screen.queryByTestId('face-detection-box')).toBeNull();
});

it('draws face boxes and identity labels on the matching processed frame', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({state:'READY',
    frame_id:'frame-12', preview:'data:image/jpeg;base64,test', preview_remaining_ms:2500,
    persons:[{box:[.05,.1,.7,.8],confidence:.88,track_id:91,identity_state:'VERIFIED',person_number:23,full_name:'Test Person'}],person_state:'READY',
    faces:[{box:[.1,.2,.3,.4],state:'VERIFIED',full_name:'Test Person',student_id:'TEST001',person_number:23,similarity:.81}]
  })));
  const camera = {id:'cam',name:'Webcam',revision:'r1',lifecycle:'ACTIVE',enabled:true} as CameraPublic;
  const {rerender} = render(<CameraRecognition camera={camera} />);
  const image = await screen.findByAltText(/Camera nh\u1eadn di\u1ec7n Webcam/);
  expect(image.getAttribute('src')).toBe('data:image/jpeg;base64,test');
  const box = screen.getByTestId('face-detection-box');
  expect(box.style.left).toBe('10%');
  expect(box.style.top).toBe('20%');
  expect(box.style.width).toBe('30%');
  expect(box.style.height).toBe('40%');
  expect(box.textContent).toContain('Test Person');
  expect(box.textContent).toContain('ID 23');
  const person = screen.getByTestId('person-detection-box');
  expect(person.style.left).toBe('5%');
  expect(person.style.height).toBe('80%');
  expect(person.textContent).toContain('Test Person');
  expect(person.textContent).toContain('ID 23');
  expect(person.textContent).not.toContain('Track #91');
  rerender(<CameraRecognition camera={{...camera,enabled:false}} />);
  expect(screen.queryByTestId('face-detection-box')).toBeNull();
  expect(screen.queryByTestId('person-detection-box')).toBeNull();
  expect(screen.queryByAltText('Camera nháº­n diá»‡n Webcam')).toBeNull();
});

it('links confirmed stranger alerts to the separate evidence report', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({state:'READY',preview:'data:image/jpeg;base64,test',unknown_alert_frames:5,alerts:[{id:'alert-1',evidence_status:'READY',evidence_key:'face-alert.jpg'}],faces:[{
    box:[.2,.2,.2,.2],state:'UNKNOWN',full_name:null,student_id:null,person_number:null,similarity:.12
  }]})));
  const camera = {id:'cam',revision:'r1',lifecycle:'ACTIVE',enabled:true} as CameraPublic;
  render(<CameraRecognition camera={camera} />);
  expect((await screen.findByRole('alert')).textContent).toMatch(/C\u1ea3nh b\u00e1o: ph\u00e1t hi\u1ec7n ng\u01b0\u1eddi l\u1ea1 trong ROI/i);
  expect(screen.getByTestId('face-detection-box').textContent).toContain('Người lạ');
  expect(screen.getByRole('link', {name: /Xem ảnh và báo cáo/}).getAttribute('href')).toBe('#alerts');
  expect(screen.queryByAltText('Snapshot cảnh báo người lạ')).toBeNull();
});

it('does not alert merely because one face is unknown', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({state:'READY', preview:'data:image/jpeg;base64,test',
    alerts:[], unknown_alert_frames:5, faces:[{box:[.2,.2,.2,.2],state:'UNKNOWN',similarity:.1}]
  })));
  render(<CameraRecognition camera={{id:'cam', revision:'r1', lifecycle:'ACTIVE', enabled:true} as CameraPublic} />);
  expect(await screen.findByText(/chờ đủ 5 frame liên tiếp/)).toBeTruthy();
  expect(screen.queryByRole('alert')).toBeNull();
  expect(screen.queryByAltText('Snapshot cảnh báo người lạ')).toBeNull();
});

it('distinguishes candidates from verified identities and stops after disable', async () => {
  const fetch = vi.fn(async () => Response.json({state:'READY',preview:'data:image/jpeg;base64,test',faces:[{
    state:'PENDING', full_name:'Test Person', student_id:'TEST001', similarity:.8
  }]}));
  vi.stubGlobal('fetch',fetch);
  const camera = {id:'cam',revision:'r1',lifecycle:'ACTIVE',enabled:true} as CameraPublic;
  const {rerender} = render(<CameraRecognition camera={camera} />);
  expect(await screen.findByText(/\u0110ang x\u00e1c minh: Test Person/)).toBeTruthy();
  expect(screen.queryByText(/ÄÃ£ xÃ¡c minh/)).toBeNull();
  rerender(<CameraRecognition camera={{...camera, enabled:false}} />);
  expect(screen.queryByText(/Test Person/)).toBeNull();
});

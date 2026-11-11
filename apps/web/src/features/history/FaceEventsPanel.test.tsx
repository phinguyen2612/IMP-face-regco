import {cleanup, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {FaceEventsPanel} from './FaceEventsPanel';

afterEach(() => {cleanup(); vi.unstubAllGlobals(); window.history.replaceState(null, '', '/');});

it('shows persisted entry crops and stranger alerts with separate evidence states', async () => {
  const fetch = vi.fn(async (_input: RequestInfo | URL) => Response.json([
    {id:'entry',kind:'FACE_CAPTURED',camera_name:'Door',recognized_at:'2026-11-02T10:00:00Z',evidence_status:'READY',evidence_key:'face-entry.jpg'},
    {id:'alert',kind:'UNKNOWN_ALERT',camera_name:'Door',recognized_at:'2026-11-02T10:00:01Z',consecutive_unknown:5,evidence_status:'FAILED',evidence_key:null}
  ]));
  vi.stubGlobal('fetch', fetch);
  render(<FaceEventsPanel cameraId="door" />);
  expect(await screen.findByText('Cảnh báo người lạ')).toBeTruthy();
  expect(screen.getByAltText('Khuôn mặt khi vào ROI').getAttribute('src')).toContain('face-entry.jpg');
  expect(screen.getByText('5 frame liên tiếp không khớp ảnh đăng ký.')).toBeTruthy();
  expect(screen.getByText(/Không lưu được ảnh; sự kiện vẫn được ghi nhận/)).toBeTruthy();
  expect(String(fetch.mock.calls[0][0])).toContain('camera_id=door');
});

it('loads the exact linked event and focuses it even when it is not in the latest page', async () => {
  const fetch = vi.fn(async (_input: RequestInfo | URL) => Response.json([
    {id:'old-event',kind:'FACE_CAPTURED',camera_name:'Old camera',recognized_at:'2026-10-01T10:00:00Z',evidence_status:'EXPIRED',evidence_key:null}
  ]));
  vi.stubGlobal('fetch', fetch);
  render(<FaceEventsPanel eventId="old-event"/>);
  const event = await screen.findByRole('article', {name:'Sự kiện đang xem'});
  expect(String(fetch.mock.calls[0][0])).toContain('event_id=old-event');
  expect(document.activeElement).toBe(event);
  expect(screen.getByText('Ảnh đã hết hạn lưu.')).toBeTruthy();
  expect(screen.queryByRole('button', {name: 'Trang sau'})).toBeNull();
});

it('explains when a linked event is unavailable', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json([])));
  render(<FaceEventsPanel eventId="missing"/>);
  expect(await screen.findByText('Không tìm thấy sự kiện này hoặc sự kiện không còn khả dụng.')).toBeTruthy();
});

it('restores the evidence page offset from the URL', async () => {
  window.history.replaceState(null, '', '/#alerts?camera=door&offset=100');
  const fetcher = vi.fn(async (_input: RequestInfo | URL) => Response.json([]));
  vi.stubGlobal('fetch', fetcher);
  render(<FaceEventsPanel cameraId="door" report/>);
  await screen.findByText('Chưa có evidence người lạ trong bộ lọc đã chọn.');
  expect(String(fetcher.mock.calls[0]?.[0])).toContain('offset=100');
  expect(window.location.hash).toContain('camera=door');
  expect(window.location.hash).toContain('offset=100');
});

import {act, cleanup, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {CameraNotifications, groupNotifications} from './CameraNotifications';

const alert = {id: 'alert-1', kind: 'UNKNOWN_ALERT', camera_name: 'Cổng chính', recognized_at: '2026-11-04T08:00:00Z', evidence_status: 'PENDING'};
afterEach(() => {cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); localStorage.clear();});

it('deduplicates persisted events, keeps read state across polling, and links to evidence', async () => {
  vi.useFakeTimers();
  const fetch = vi.fn(async () => Response.json([alert, alert]));
  vi.stubGlobal('fetch', fetch);
  const {unmount} = render(<CameraNotifications userId="admin-1"/>);
  await act(async () => {await vi.advanceTimersByTimeAsync(0);});
  const trigger = screen.getByRole('button', {name: 'Thông báo camera, 1 chưa đọc'});
  act(() => trigger.click());
  expect(screen.getAllByText('Cảnh báo người lạ')).toHaveLength(1);
  act(() => screen.getByRole('button', {name: 'Đọc tất cả'}).click());
  expect(screen.getByRole('button', {name: 'Thông báo camera'})).toBeTruthy();
  fetch.mockImplementation(async () => Response.json([{...alert, evidence_status: 'READY'}, {...alert, id: 'alert-2'}]));
  await act(async () => {await vi.advanceTimersByTimeAsync(3000);});
  expect(screen.getByRole('button', {name: 'Thông báo camera, 1 chưa đọc'})).toBeTruthy();
  const eventLink = screen.getAllByRole('link', {name: /Xem evidence người lạ/})[1];
  expect(eventLink.getAttribute('href')).toBe('#alerts?event=alert-2');
  act(() => eventLink.click());
  expect(screen.queryByRole('region', {name: 'Sự kiện camera'})).toBeNull();
  expect(JSON.parse(localStorage.getItem('camera-notifications-read:admin-1')!)).toEqual(['alert-1', 'alert-2']);
  unmount();
  await act(async () => {await vi.advanceTimersByTimeAsync(10000);});
  expect(fetch).toHaveBeenCalledTimes(2);
  render(<CameraNotifications userId="admin-1"/>);
  await act(async () => {await vi.advanceTimersByTimeAsync(0);});
  expect(screen.getByRole('button', {name: 'Thông báo camera'})).toBeTruthy();
});

it('shows connection errors, recovers on retry, and supports Escape', async () => {
  vi.useFakeTimers();
  const fetch = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(Response.json([]));
  vi.stubGlobal('fetch', fetch);
  render(<CameraNotifications userId="admin-2"/>);
  await act(async () => {await vi.advanceTimersByTimeAsync(0);});
  act(() => screen.getByRole('button', {name: 'Thông báo camera'}).click());
  expect(screen.getByRole('alert').textContent).toContain('Không cập nhật được thông báo');
  await act(async () => {await vi.advanceTimersByTimeAsync(3000);});
  expect(screen.queryByRole('alert')).toBeNull();
  expect(screen.getByText('Chưa có sự kiện camera.')).toBeTruthy();
  act(() => document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'})));
  expect(screen.queryByRole('region', {name: 'Sự kiện camera'})).toBeNull();
  expect(document.activeElement).toBe(screen.getByRole('button', {name: 'Thông báo camera'}));
});


it('groups nearby events only within the same camera and kind', () => {
  const rows = [
    {...alert, camera_id: 'a', id: '1'},
    {...alert, camera_id: 'a', id: '2', recognized_at: '2026-11-04T08:00:20Z'},
    {...alert, camera_id: 'b', id: '3'},
    {...alert, camera_id: 'a', id: '4', recognized_at: '2026-11-04T08:01:00Z'},
  ] as Parameters<typeof groupNotifications>[0];
  const groups = groupNotifications(rows);
  expect(groups).toHaveLength(3);
  expect(groups.find(group => group.event.id === '2')?.ids).toEqual(['2', '1']);
});

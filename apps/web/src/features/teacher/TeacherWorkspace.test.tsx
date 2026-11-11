import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { TeacherWorkspace } from './TeacherWorkspace';

const api = vi.hoisted(() => ({ listTeacherClasses: vi.fn(), listTeacherSessions: vi.fn(), listTeacherCameras: vi.fn(), getSessionAttendance: vi.fn(), listPendingFaceReviews: vi.fn(), createTeacherSession: vi.fn(), completeTeacherSession: vi.fn(), reviewFaceImage: vi.fn() }));
vi.mock('../../api/classes', () => api);
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it('does not show an empty review queue while loading or after a request failure', async () => {
  let reject!: (reason: Error) => void;
  api.listPendingFaceReviews.mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
  render(<TeacherWorkspace page="teacher/review" />);
  expect(screen.getByRole('status').textContent).toContain('Đang tải');
  expect(screen.queryByText('Không có ảnh chờ duyệt')).toBeNull();
  await act(async () => { reject(new Error('Mất kết nối')); });
  expect(screen.getByRole('alert').textContent).toContain('Mất kết nối');
  expect(screen.queryByText('Không có ảnh chờ duyệt')).toBeNull();
});

it('discards attendance arriving after the teacher switches class', async () => {
  api.listTeacherClasses.mockResolvedValue([{ id: 'a', name: 'Lớp A' }, { id: 'b', name: 'Lớp B' }]);
  api.listTeacherSessions.mockImplementation(async (id: string) => id === 'a' ? [{ id: 's1', classroom_id: 'a', label: 'Buổi A', starts_at: '2026-11-06T01:00:00Z', state: 'SCHEDULED', done: true }] : []);
  api.listTeacherCameras.mockResolvedValue([]);
  let resolve!: (value: { items: unknown[] }) => void;
  api.getSessionAttendance.mockReturnValue(new Promise(done => { resolve = done; }));
  const user = userEvent.setup(); render(<TeacherWorkspace page="teacher/classes" />);
  await user.click(await screen.findByRole('button', { name: 'Xem điểm danh' }));
  fireEvent.change(screen.getByLabelText('Lớp của tôi'), { target: { value: 'b' } });
  await act(async () => { resolve({ items: [{ person_id: 'old', full_name: 'Kết quả lớp cũ', status: 'PRESENT' }] }); });
  expect(screen.queryByText('Kết quả lớp cũ')).toBeNull();
  expect(await screen.findByText('Chưa có buổi điểm danh')).toBeTruthy();
});

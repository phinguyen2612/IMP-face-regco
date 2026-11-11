import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { StudentWorkspace } from './StudentWorkspace';

const api = vi.hoisted(() => ({ listMyAttendance: vi.fn(), listMyFaceImages: vi.fn() }));
vi.mock('../../api/student', () => ({ ...api, getMyProfile: vi.fn(), listMyEvents: vi.fn(), uploadMyFaceImages: vi.fn(), myFaceImageUrl: vi.fn(), myEventEvidenceUrl: vi.fn(), loadPrivateImage: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it('shows loading until attendance is received, then shows the real empty state', async () => {
  let resolve!: (value: []) => void;
  api.listMyAttendance.mockReturnValue(new Promise(done => { resolve = done; }));
  render(<StudentWorkspace page="me/attendance" />);
  expect(screen.getByRole('status').textContent).toContain('Đang tải');
  expect(screen.queryByText('Chưa có lượt điểm danh')).toBeNull();
  await act(async () => { resolve([]); });
  expect(screen.getByText('Chưa có lượt điểm danh')).toBeTruthy();
});

it('does not present an enrollment request failure as an empty gallery', async () => {
  api.listMyFaceImages.mockRejectedValue(new Error('Không có quyền xem ảnh'));
  render(<StudentWorkspace page="me/enrollment" />);
  expect((await screen.findByRole('alert')).textContent).toContain('Không có quyền xem ảnh');
  expect(screen.queryByText('Chưa có ảnh đăng ký')).toBeNull();
  expect(screen.getByLabelText('Chọn ảnh khuôn mặt').hidden).toBe(false);
});

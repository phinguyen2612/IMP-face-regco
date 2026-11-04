import {cleanup, render, screen, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach, expect, it, vi} from 'vitest';
import {AlertsPage} from './AlertsPage';

afterEach(() => {cleanup(); vi.unstubAllGlobals(); window.history.replaceState(null, '', '/');});

it('requests only stranger evidence and applies camera and date filters', async () => {
  const fetch = vi.fn(async (input: RequestInfo | URL) => Response.json(String(input).includes('/face-events') ? [] : {items: [{id: 'gate', name: 'Cổng chính'}]}));
  vi.stubGlobal('fetch', fetch);
  const user = userEvent.setup();
  render(<AlertsPage/>);
  await screen.findByText('Chưa có evidence người lạ trong bộ lọc đã chọn.');
  expect(screen.queryByLabelText('Loại sự kiện')).toBeNull();
  await user.selectOptions(screen.getByLabelText('Camera'), 'gate');
  await user.type(screen.getByLabelText('Từ ngày'), '2026-11-01');
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes('kind=UNKNOWN_ALERT') && String(url).includes('camera_id=gate') && String(url).includes('start=2026-11-01'))).toBe(true));
  expect(screen.getByRole('button', {name: 'Xuất báo cáo trang này (CSV)'}).hasAttribute('disabled')).toBe(true);
});

it('restores the filters from a detail return link', async () => {
  window.history.replaceState(null, '', '/#alerts?camera=gate&start=2026-11-01');
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => Response.json(String(input).includes('/face-events') ? [] : {items: [{id: 'gate', name: 'Cổng chính'}]})));
  render(<AlertsPage/>);
  await screen.findByRole('option', {name: 'Cổng chính'});
  expect((screen.getByLabelText('Camera') as HTMLSelectElement).value).toBe('gate');
  expect((screen.getByLabelText('Từ ngày') as HTMLInputElement).value).toBe('2026-11-01');
});

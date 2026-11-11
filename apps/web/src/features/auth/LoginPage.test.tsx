import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { ThemeProvider } from '../../ui/ThemeProvider';
import { LoginPage } from './LoginPage';

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); document.documentElement.removeAttribute('data-theme'); });
function renderLogin(onSignIn = vi.fn(async () => {})) {
  return render(<ThemeProvider><LoginPage onSignIn={onSignIn} error={null} onRetry={() => {}} /></ThemeProvider>);
}

it('persists the pause preference and restores it after remount', async () => {
  const user = userEvent.setup();
  const first = renderLogin();
  await user.click(screen.getByRole('button', { name: 'Tạm dừng hiệu ứng' }));
  expect(screen.getByRole('main').getAttribute('data-motion')).toBe('paused');
  first.unmount(); renderLogin();
  expect(screen.getByRole('button', { name: 'Bật hiệu ứng' })).toBeTruthy();
  await user.click(screen.getByRole('button', { name: 'Bật hiệu ứng' }));
  expect(localStorage.getItem('face-attendance-login-motion')).toBe('enabled');
});

it('honors reduced motion and reacts to system preference changes', () => {
  let onChange: (() => void) | undefined;
  const query = { matches: true, addEventListener: vi.fn((_type, listener) => { onChange = listener; }), removeEventListener: vi.fn() };
  vi.stubGlobal('matchMedia', vi.fn((value: string) => value.includes('reduced-motion') ? query : { matches: false }));
  const { unmount } = renderLogin();
  expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Đã giảm chuyển động' }).disabled).toBe(true);
  expect(screen.getByRole('main').getAttribute('data-motion')).toBe('paused');
  act(() => { query.matches = false; onChange?.(); });
  expect(screen.getByRole('button', { name: 'Tạm dừng hiệu ứng' })).toBeTruthy();
  unmount(); expect(query.removeEventListener).toHaveBeenCalledWith('change', onChange);
});

it('pauses while the document is hidden and resumes only when enabled', () => {
  const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(false);
  renderLogin(); expect(screen.getByRole('main').getAttribute('data-motion')).toBe('running');
  hidden.mockReturnValue(true); fireEvent(document, new Event('visibilitychange'));
  expect(screen.getByRole('main').getAttribute('data-motion')).toBe('paused');
  hidden.mockReturnValue(false); fireEvent(document, new Event('visibilitychange'));
  expect(screen.getByRole('main').getAttribute('data-motion')).toBe('running');
});

it('works with blocked storage and keeps password visibility accessible', async () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new DOMException('Blocked'); });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('Blocked'); });
  const user = userEvent.setup(); renderLogin();
  await user.click(screen.getByRole('button', { name: 'Tạm dừng hiệu ứng' }));
  expect(screen.getByRole('button', { name: 'Bật hiệu ứng' })).toBeTruthy();
  await user.type(screen.getByLabelText('Mật khẩu'), 'secret');
  await user.click(screen.getByRole('button', { name: 'Hiện mật khẩu' }));
  expect(screen.getByLabelText<HTMLInputElement>('Mật khẩu').type).toBe('text');
  await user.click(screen.getByRole('button', { name: 'Ẩn mật khẩu' }));
  expect(screen.getByLabelText<HTMLInputElement>('Mật khẩu').type).toBe('password');
});

it('blocks duplicate submissions and keeps API errors by the form', async () => {
  let reject!: (reason: Error) => void;
  const signIn = vi.fn(() => new Promise<void>((_resolve, fail) => { reject = fail; }));
  const user = userEvent.setup(); renderLogin(signIn);
  await user.type(screen.getByLabelText('Email'), 'student@example.test');
  await user.type(screen.getByLabelText('Mật khẩu'), 'secret');
  const form = screen.getByLabelText('Email').closest('form')!;
  fireEvent.submit(form); fireEvent.submit(form);
  expect(signIn).toHaveBeenCalledTimes(1);
  expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Đang xác thực…' }).disabled).toBe(true);
  await act(async () => { reject(new Error('Sai tài khoản hoặc mật khẩu')); });
  expect(screen.getByRole('alert').textContent).toBe('Sai tài khoản hoặc mật khẩu');
  expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Đăng nhập' }).disabled).toBe(false);
});

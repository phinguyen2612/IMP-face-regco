import {useEffect, useRef, useState} from 'react';
import type {UserRole} from '../api/auth';
import {Icon} from './Icon';

export function AccountMenu({email, role, onSignOut}: {email: string; role: UserRole; onSignOut: () => Promise<void>}) {
  const menu = useRef<HTMLDetailsElement>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const outside = (event: PointerEvent) => {if (menu.current && !menu.current.contains(event.target as Node)) menu.current.open = false;};
    const escape = (event: KeyboardEvent) => {if (event.key === 'Escape' && menu.current?.open) {menu.current.open = false; menu.current.querySelector('summary')?.focus();}};
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape);};
  }, []);
  return <details ref={menu} className="account-menu">
    <summary aria-label={`Tài khoản: ${email}`}><span className="account-avatar" aria-hidden="true">{email.slice(0, 2).toUpperCase()}</span><span className="account-caption">{role === 'ADMIN' ? 'Quản trị viên' : role === 'TEACHER' ? 'Giáo viên' : 'Sinh viên'}<small>Tài khoản của tôi</small></span><span aria-hidden="true">⌄</span></summary>
    <div className="account-panel"><strong>{email}</strong><p>{role === 'ADMIN' ? 'Không gian quản trị' : role === 'TEACHER' ? 'Không gian giảng dạy' : 'Không gian sinh viên'}</p><button type="button" disabled={busy} onClick={() => {setBusy(true); void onSignOut().finally(() => setBusy(false));}}><Icon name="logout"/>{busy ? 'Đăng xuất…' : 'Đăng xuất'}</button></div>
  </details>;
}

import { useRef, useState, type FormEvent } from "react";
import fptLogo from "../../assets/fpt-university-logo.png";
import { ThemeToggle } from "../../ui/ThemeToggle";
import {Icon} from '../../ui/Icon';
import { LoginBackdrop } from './LoginBackdrop';
import { useLoginMotion } from './useLoginMotion';

export function LoginPage({
  onSignIn,
  error,
  onRetry,
}: {
  onSignIn: (email: string, password: string) => Promise<void>;
  error: string | null;
  onRetry: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const submitting = useRef(false);
  const motion = useLoginMotion();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setFormError(null);
    try {
      await onSignIn(email.trim(), password);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Không thể đăng nhập.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return <main className="login-page" data-motion={motion.running ? 'running' : 'paused'}>
    <div className="login-ambient" aria-hidden="true"><span /><span /></div>
    <header className="login-brand">
      <img src={fptLogo} alt="Trường Đại học FPT" />
      <div className="login-preferences">
        <button type="button" className="login-motion-toggle" onClick={motion.toggle} disabled={motion.reduced}
          title={motion.reduced ? 'Đang dùng cài đặt giảm chuyển động của thiết bị' : undefined}>
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
            {motion.enabled && !motion.reduced ? <path d="M7 4v12 M13 4v12" /> : <path d="m7 4 9 6-9 6V4Z" />}
          </svg>
          {motion.reduced ? 'Đã giảm chuyển động' : motion.enabled ? 'Tạm dừng hiệu ứng' : 'Bật hiệu ứng'}
        </button>
        <ThemeToggle />
      </div>
    </header>
    <div className="login-layout">
    <aside className="login-context" aria-label="Giới thiệu không gian làm việc">
      <p className="eyebrow"><span /> CAMPUS WORKSPACE</p>
      <h2>Nhận diện rõ ràng.<br /><em>Kết nối mỗi ngày.</em></h2>
      <p>Một không gian cho camera, nhận diện và điểm danh.<br className="login-desktop-break" /> Để mỗi ngày đến lớp thuận tiện hơn.</p>
      <LoginBackdrop />
      <div className="login-capabilities">
        <div><Icon name="camera" /><span><strong>Giám sát camera</strong><small>Theo dõi nguồn hình</small></span></div>
        <div><Icon name="image" /><span><strong>Tra cứu minh chứng</strong><small>Đúng lúc, đúng ngữ cảnh</small></span></div>
        <div><Icon name="check" /><span><strong>Quản lý điểm danh</strong><small>Theo lớp và vai trò</small></span></div>
      </div>
    </aside>
    <section className="login-card" aria-labelledby="login-title">
      <div className="login-card-mark" aria-hidden="true"><Icon name="grid" /></div>
      <p className="eyebrow">KHÔNG GIAN HỌC TẬP</p>
      <h1 id="login-title">Đăng nhập</h1>
      <p className="login-intro">Chào mừng bạn trở lại. Sử dụng tài khoản do quản trị viên cấp để tiếp tục.</p>
      {(formError || error) && <p id="login-error" className="login-error" role="alert">{formError ?? error}</p>}
      {error && !formError && <button type="button" className="login-retry" disabled={busy} onClick={onRetry}>Thử kết nối lại <Icon name="arrow" /></button>}
      <form onSubmit={submit} aria-busy={busy} aria-describedby={formError || error ? 'login-error' : undefined}>
        <div className="login-field"><label htmlFor="login-email">Email</label><input id="login-email" name="email" type="email" autoComplete="username" placeholder="ban@fpt.edu.vn" required value={email} onChange={event => setEmail(event.target.value)} /></div>
        <div className="login-field"><label htmlFor="login-password">Mật khẩu</label><div className="login-password-field">
          <input id="login-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Nhập mật khẩu của bạn" required value={password} onChange={event => setPassword(event.target.value)} />
          <button type="button" className="login-password-toggle" aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'} aria-controls="login-password" onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Ẩn' : 'Hiện'}</button>
        </div></div>
        <button className="login-submit" type="submit" disabled={busy}>{busy ? 'Đang xác thực…' : 'Đăng nhập'}{!busy && <Icon name="arrow" />}</button>
      </form>
      <p className="login-footnote"><Icon name="check" />Phiên làm việc kết thúc khi bạn đăng xuất.</p>
      <div className="login-card-footer"><span>Dành cho</span><p>Quản trị viên <i /> Giáo viên <i /> Sinh viên</p></div>
    </section>
    </div>
    <footer className="login-footer"><span>FPT University <span aria-hidden="true">/</span> Điểm danh thông minh</span><span>Học tập kết nối. Quản lý thuận tiện.</span></footer>
  </main>;
}

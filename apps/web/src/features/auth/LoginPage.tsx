import { useState, type FormEvent } from "react";
import fptLogo from "../../assets/fpt-university-logo.png";
import { ThemeToggle } from "../../ui/ThemeToggle";
import {Icon} from '../../ui/Icon';

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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await onSignIn(email.trim(), password);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Không thể đăng nhập.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="login-page">
    <aside className="login-context" aria-label="Giới thiệu không gian làm việc"><p className="eyebrow">CAMPUS WORKSPACE</p><h2>Nhận diện rõ ràng.<br/>Điểm danh thuận tiện.</h2><p>Không gian làm việc dành cho quản trị viên, giáo viên và sinh viên.</p><div className="login-capabilities"><div><Icon name="camera"/><span><strong>Giám sát camera</strong><small>Theo dõi nguồn hình và sự kiện</small></span></div><div><Icon name="image"/><span><strong>Tra cứu minh chứng</strong><small>Camera, thời điểm và ảnh trong cùng ngữ cảnh</small></span></div><div><Icon name="check"/><span><strong>Quản lý điểm danh</strong><small>Thông tin theo đúng lớp và vai trò</small></span></div></div><span className="login-context-footer">FPT University · Điểm danh thông minh</span></aside>
    <section className="login-card" aria-labelledby="login-title">
      <div className="login-brand"><img src={fptLogo} alt="Trường Đại học FPT" /><ThemeToggle/></div>
      <p className="eyebrow">KHÔNG GIAN HỌC TẬP</p>
      <h1 id="login-title">Đăng nhập</h1>
      <p className="login-intro">Đăng nhập bằng tài khoản do quản trị viên cấp để tiếp tục.</p>
      {(formError || error) && <p className="error" role="alert">{formError ?? error}</p>}
      {error && !formError && <button type="button" className="secondary-button" onClick={onRetry}>Thử kết nối lại</button>}
      <form onSubmit={submit}>
        <label>Email<input type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} /></label>
        <label>Mật khẩu<input type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} /></label>
        <button type="submit" disabled={busy}>{busy ? "Đang xác thực…" : "Đăng nhập"}</button>
      </form>
      <p className="login-footnote">Phiên đăng nhập được bảo vệ và tự kết thúc khi bạn đăng xuất.</p>
    </section>
  </main>;
}

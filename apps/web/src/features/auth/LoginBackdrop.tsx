import { Icon } from '../../ui/Icon';

/** Decorative geometry only: these panels never represent live recognition data. */
export function LoginBackdrop() {
  return <div className="login-scene" aria-hidden="true">
    <div className="login-scene-orbit" />
    <div className="login-scene-floor" />
    <div className="login-scene-object">
      <div className="login-scene-frame login-scene-frame-back"><span /><span /><span /></div>
      <div className="login-scene-frame login-scene-frame-middle"><div className="login-scene-matrix">{Array.from({ length: 12 }, (_, i) => <i key={i} />)}</div></div>
      <div className="login-scene-frame login-scene-frame-front">
        <div className="login-scene-caption"><span>CAMPUS</span><span>01 / 03</span></div>
        <div className="login-scene-lens"><Icon name="camera" /><i /><i /><i /><i /></div>
        <div className="login-scene-baseline"><span /><span /><Icon name="grid" /></div>
      </div>
    </div>
    <span className="login-scene-coordinate">KHÔNG GIAN KẾT NỐI</span>
  </div>;
}

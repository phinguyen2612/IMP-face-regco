import { useEffect, useState } from "react";
import { connectRuntimeStatus, getHealth, type HealthStatus } from "../api/client";
import type { RuntimeStatus } from "../api/contracts";
import { AdminManagement } from "../features/admin/AdminManagement";
import { LoginPage } from "../features/auth/LoginPage";
import { SessionProvider, useSession } from "../features/auth/SessionProvider";
import { CameraPanel } from "../features/cameras/CameraPanel";
import {LivewallPage} from "../features/monitoring/LivewallPage";
import { SystemStatus } from "../features/monitoring/SystemStatus";
import { MonitoringPage } from "../features/monitoring/MonitoringPage";
import { CameraNotifications } from "../features/alerts/CameraNotifications";
import { AlertsPage } from "../features/alerts/AlertsPage";
import { CameraEventDetails } from "../features/history/CameraEventDetails";
import { RecognitionHistoryPanel } from "../features/history/RecognitionHistoryPanel";
import { ModelsPanel } from "../features/models/ModelsPanel";
import { FaceRegistryPanel } from "../features/registry/FaceRegistryPanel";
import { StudentWorkspace } from "../features/student/StudentWorkspace";
import { TeacherWorkspace } from "../features/teacher/TeacherWorkspace";
import { AccountMenu } from "../ui/AccountMenu";
import { PageHeader } from "../ui/PageHeader";
import { ThemeToggle } from "../ui/ThemeToggle";
import { ThemeProvider } from "../ui/ThemeProvider";
import { defaultPage, pagesForRole, Sidebar, workspacePages, type WorkspacePage } from "./Sidebar";

function AppContent() {
 const session=useSession();
 if(session.status==="loading")return <main className="session-loading" role="status">Đang kiểm tra phiên đăng nhập…</main>;
 if(session.status==="anonymous"||session.status==="error")return <LoginPage onSignIn={session.signIn} error={session.status==="error"?session.error:null} onRetry={session.retry}/>;
 if(!session.user)return <LoginPage onSignIn={session.signIn} error={null} onRetry={session.retry}/>;
 return <Workspace key={session.user.user_id} user={session.user} onSignOut={session.signOut}/>;
}

function Workspace({user,onSignOut}:{user:NonNullable<ReturnType<typeof useSession>["user"]>;onSignOut:()=>Promise<void>}) {
 const rolePages=pagesForRole(user.role);
 const initial=()=>{const hash=window.location.hash.slice(1).split("?")[0];return hash&&Object.hasOwn(workspacePages,hash)?hash as WorkspacePage:defaultPage(user.role);};
 const [page,setPage]=useState<WorkspacePage>(initial);
 const [eventId,setEventId]=useState(()=>new URLSearchParams(window.location.hash.split("?")[1]).get("event") ?? "");
 const [health,setHealth]=useState<HealthStatus|null>(null);const [error,setError]=useState<string|null>(null);const [runtimeStatuses,setRuntimeStatuses]=useState<RuntimeStatus[]>([]);const [menuOpen,setMenuOpen]=useState(false);
 const allowed=rolePages.includes(page);const info=workspacePages[page];
 useEffect(()=>{const navigate=()=>{const hash=window.location.hash.slice(1).split("?")[0];if(Object.hasOwn(workspacePages,hash))setPage(hash as WorkspacePage);setEventId(new URLSearchParams(window.location.hash.split("?")[1]).get("event") ?? "");setMenuOpen(false);};window.addEventListener("hashchange",navigate);return()=>window.removeEventListener("hashchange",navigate);},[]);
 useEffect(()=>{if(!menuOpen)return;const previous=document.activeElement as HTMLElement|null;const elements=Array.from(document.querySelectorAll<HTMLElement>("#workspace-sidebar a, #workspace-sidebar button"));elements[0]?.focus();const keydown=(event:KeyboardEvent)=>{if(event.key==="Escape"){setMenuOpen(false);return;}if(event.key!=="Tab")return;const first=elements[0],last=elements[elements.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}};const resize=()=>{if(window.innerWidth>900)setMenuOpen(false);};window.addEventListener("keydown",keydown);window.addEventListener("resize",resize);return()=>{window.removeEventListener("keydown",keydown);window.removeEventListener("resize",resize);previous?.focus();};},[menuOpen]);
 useEffect(()=>{
  if(user.role!=="ADMIN")return;
  let disposed=false; let timer: ReturnType<typeof setTimeout>;
  async function refreshHealth(){try{const value=await getHealth();if(!disposed){setHealth(value);setError(null);}}catch{if(!disposed){setHealth(null);setError("API kh\u00f4ng ph\u1ea3n h\u1ed3i");}}finally{if(!disposed)timer=setTimeout(()=>void refreshHealth(),15000);}}
  void refreshHealth();
  const disconnect=connectRuntimeStatus(next=>setRuntimeStatuses(current=>[...current.filter(item=>item.camera_id!==next.camera_id).slice(-255),next]));
  return()=>{disposed=true;clearTimeout(timer);disconnect();};
 },[user.role]);
 const apiOnline=health?.status==="ok";
 return <div className="app-shell"><a className="skip-link" href="#workspace-content" onClick={event=>{event.preventDefault();document.getElementById("workspace-content")?.focus();}}>Đi đến nội dung</a>
  {menuOpen&&<button className="sidebar-backdrop" aria-label="Đóng điều hướng" onClick={()=>setMenuOpen(false)}/>}
  <Sidebar page={page} open={menuOpen} onNavigate={()=>setMenuOpen(false)} role={user.role}/>
  <div className="workspace-shell" inert={menuOpen}><header className="workspace-topbar"><button className="menu-toggle" aria-label="Mở điều hướng" aria-expanded={menuOpen} aria-controls="workspace-sidebar" onClick={()=>setMenuOpen(!menuOpen)}>☰</button><span className="workspace-breadcrumb">Không gian làm việc <span>/</span> <strong>{info.label}</strong></span>{user.role==="ADMIN"&&<span className={`api-status ${apiOnline?'is-online':''}`} role="status"><i aria-hidden="true"/>{apiOnline?"API đã kết nối":error??"Đang kiểm tra API…"}</span>}<div className="topbar-actions">{user.role==="ADMIN"&&<CameraNotifications userId={user.user_id}/>}<ThemeToggle/><AccountMenu email={user.email} role={user.role} onSignOut={onSignOut}/></div></header>
   <main className="workspace-content" id="workspace-content" tabIndex={-1}><PageHeader group={info.group} title={info.label} description={info.description}/>
    {!allowed?<section className="workspace-card access-denied" role="alert"><h2>Không có quyền truy cập</h2><p>Tài khoản của bạn không có quyền mở mục này.</p><a className="primary-action" href={`#${defaultPage(user.role)}`}>Về không gian của tôi</a></section>:
      eventId&&(page==="alerts"||page==="history")?<CameraEventDetails key={`${page}:${eventId}`} eventId={eventId} page={page}/>:page==="overview"||page==="monitoring"?<MonitoringPage statuses={runtimeStatuses} overview={page==="overview"}/>:page==="livewall"?<LivewallPage statuses={runtimeStatuses}/>:page==="alerts"?<AlertsPage/>:page==="cameras"?<CameraPanel runtimeStatuses={runtimeStatuses}/>:page==="people"?<FaceRegistryPanel/>:page==="history"?<RecognitionHistoryPanel/>:page==="models"?<ModelsPanel/>:page==="system"?<SystemStatus statuses={runtimeStatuses}/>:page==="accounts"||page==="classes"?<AdminManagement key={page} page={page}/>:page.startsWith("teacher/")?<TeacherWorkspace key={page} page={page}/>:<StudentWorkspace key={page} page={page}/>}</main>
  </div>
 </div>;
}

export function App(){return <ThemeProvider><SessionProvider><AppContent/></SessionProvider></ThemeProvider>;}

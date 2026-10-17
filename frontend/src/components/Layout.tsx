import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { isAdmin, isManager, ROLE_LABELS } from '../lib/roles'
import NotificationBell from './NotificationBell'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/dashboard" className="brand"><span className="sidebar-brand-mark">✓</span>TaskFlow</Link>
        <span className="sidebar-caption">WORKSPACE</span>
        <nav aria-label="Workspace navigation">
          <NavLink to="/dashboard"><span aria-hidden="true">▦</span> Dashboard</NavLink>
          <NavLink to="/tasks"><span aria-hidden="true">✓</span> Tasks</NavLink>
          <NavLink to="/projects"><span aria-hidden="true">▤</span> Projects</NavLink>
          <NavLink to="/calendar"><span aria-hidden="true">◷</span> Calendar</NavLink>
          <NavLink to="/notifications"><span aria-hidden="true">♧</span> Notifications</NavLink>
          {isAdmin(user?.role) && (
            <>
              <div className="nav-section">Administration</div>
              <NavLink to="/admin/users"><span aria-hidden="true">♙</span> Users</NavLink>
              <NavLink to="/admin/statuses"><span aria-hidden="true">◉</span> Task statuses</NavLink>
              <NavLink to="/admin/priorities"><span aria-hidden="true">⚑</span> Priorities</NavLink>
              <NavLink to="/admin/tags"><span aria-hidden="true">⌑</span> Tags</NavLink>
              <NavLink to="/admin/settings"><span aria-hidden="true">⚙</span> System settings</NavLink>
              <NavLink to="/admin/audit"><span aria-hidden="true">≡</span> Audit log</NavLink>
            </>
          )}
          {isManager(user?.role) && <><div className="nav-section">INSIGHTS</div><NavLink to="/reports"><span aria-hidden="true">▥</span> Reports</NavLink></>}
        </nav>
        <div className="sidebar-footer">
          <Link to="/profile" className="sidebar-user">
            <span className="sidebar-avatar">{(user?.first_name || user?.username || 'U').slice(0, 1).toUpperCase()}</span>
            <span className="user-chip"><strong>{user?.first_name || user?.username}</strong><small>{user && ROLE_LABELS[user.role]}</small></span>
            <span aria-hidden="true">···</span>
          </Link>
          <button className="sidebar-logout" onClick={handleLogout}>↪ <span>Log out</span></button>
        </div>
      </aside>
      <main className="content">
        <div className="workspace-main">
          <div className="topbar">
            <div className="workspace-breadcrumb"><span>TaskFlow</span><span aria-hidden="true">/</span><strong>Workspace</strong></div>
            <div className="topbar-actions"><NotificationBell /><Link to="/profile" className="topbar-user">{user?.first_name || user?.username}</Link></div>
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  )
}

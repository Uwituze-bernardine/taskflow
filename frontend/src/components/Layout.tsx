import { NavLink, Outlet, useNavigate } from 'react-router-dom'
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
        <div className="brand">TaskFlow</div>
        <nav>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/projects">Projects</NavLink>
          <NavLink to="/tasks">Tasks</NavLink>
          <NavLink to="/calendar">Calendar</NavLink>
          <NavLink to="/notifications">Notifications</NavLink>
          {isManager(user?.role) && <NavLink to="/reports">Reports</NavLink>}
          <NavLink to="/profile">My profile</NavLink>
          {isAdmin(user?.role) && (
            <>
              <div className="nav-section">Administration</div>
              <NavLink to="/admin/users">Users</NavLink>
              <NavLink to="/admin/statuses">Task statuses</NavLink>
              <NavLink to="/admin/priorities">Priorities</NavLink>
              <NavLink to="/admin/tags">Tags</NavLink>
              <NavLink to="/admin/settings">System settings</NavLink>
              <NavLink to="/admin/audit">Audit log</NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            {user?.first_name || user?.username}
            <br />
            {user && ROLE_LABELS[user.role]}
          </div>
          <button onClick={handleLogout}>Log out</button>
        </div>
      </aside>
      <main className="content">
        <div className="topbar"><NotificationBell /></div>
        <Outlet />
      </main>
    </div>
  )
}

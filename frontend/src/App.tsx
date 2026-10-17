import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireRole from './components/RequireRole'
import ProtectedRoute from './components/ProtectedRoute'
import Calendar from './pages/Calendar'
import Dashboard from './pages/Dashboard'
import AdminPriorities from './pages/AdminPriorities'
import AdminSettings from './pages/AdminSettings'
import AdminStatuses from './pages/AdminStatuses'
import AdminTags from './pages/AdminTags'
import AuditLog from './pages/AuditLog'
import AdminUsers from './pages/AdminUsers'
import Home from './pages/Home'
import Login from './pages/Login'
import Notifications from './pages/Notifications'
import Profile from './pages/Profile'
import Reports from './pages/Reports'
import Register from './pages/Register'
import ProjectDetail from './pages/ProjectDetail'
import Projects from './pages/Projects'
import TaskDetail from './pages/TaskDetail'
import Tasks from './pages/Tasks'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/tasks/:id" element={<TaskDetail />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/profile" element={<Profile />} />
          <Route element={<RequireRole roles={['ADMIN', 'PROJECT_MANAGER', 'TEAM_LEADER']} />}>
            <Route path="/reports" element={<Reports />} />
          </Route>
          <Route element={<RequireRole roles={['ADMIN']} />}>
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/statuses" element={<AdminStatuses />} />
            <Route path="/admin/priorities" element={<AdminPriorities />} />
            <Route path="/admin/tags" element={<AdminTags />} />
            <Route path="/admin/settings" element={<AdminSettings />} />
            <Route path="/admin/audit" element={<AuditLog />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import type { Role } from '../types'

/**
 * FR-006: route-level access control. Wrap routes that only some roles may open.
 * (The backend enforces the same rule; this keeps people out of screens that would only show errors.)
 */
export default function RequireRole({ roles }: { roles: Role[] }) {
  const { user } = useAuth()
  if (!user || !roles.includes(user.role)) return <Navigate to="/dashboard" replace />
  return <Outlet />
}

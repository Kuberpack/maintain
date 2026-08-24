import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import type { UserRole } from '../api/types'

export function ProtectedRoute() {
  const { user } = useAuth()
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

export function RoleRoute({ roles }: { roles: UserRole[] }) {
  const { user } = useAuth()
  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (!roles.includes(user.role)) {
    return <Navigate to={user.role === 'operator' ? '/today' : '/'} replace />
  }
  return <Outlet />
}

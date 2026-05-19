import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/useStore'

export default function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  const loc = useLocation()
  if (!token) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  }
  return <Outlet />
}

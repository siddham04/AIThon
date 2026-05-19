import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import ProtectedRoute from './components/auth/ProtectedRoute'
import AppShell from './components/layout/AppShell'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import NewProject from './pages/NewProject'
import Dashboard from './pages/Dashboard'
import StakeholderPreview from './pages/StakeholderPreview'
import AnalyticsRoute from './pages/AnalyticsRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/new" element={<NewProject />} />
            <Route path="/project/:id" element={<Dashboard />} />
            <Route path="/project/:id/preview" element={<StakeholderPreview />} />
            <Route path="/project/:id/analytics" element={<AnalyticsRoute />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

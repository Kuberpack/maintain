import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/useAuth'
import { ProtectedRoute } from './components/ProtectedRoute'
import { NavBar } from './components/NavBar'
import { LoginPage } from './pages/LoginPage'
import { MachineListPage } from './pages/MachineListPage'
import { MachineDetailPage } from './pages/MachineDetailPage'
import { OverduePage } from './pages/OverduePage'
import { SummaryPage } from './pages/SummaryPage'
import { UsersPage } from './pages/UsersPage'

function Layout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <Outlet />
    </div>
  )
}

function AppRoutes() {
  const { isLoading } = useAuth()

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-slate-500">Loading…</div>
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<MachineListPage />} />
          <Route path="/machines/:id" element={<MachineDetailPage />} />
          <Route path="/overdue" element={<OverduePage />} />
          <Route path="/summary" element={<SummaryPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App

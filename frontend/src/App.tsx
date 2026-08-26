import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/useAuth'
import { LocaleProvider } from './locale/LocaleProvider'
import { ProtectedRoute, RoleRoute } from './components/ProtectedRoute'
import { NavBar } from './components/NavBar'
import { LoginPage } from './pages/LoginPage'
import { MachineListPage } from './pages/MachineListPage'
import { MachineDetailPage } from './pages/MachineDetailPage'
import { OverduePage } from './pages/OverduePage'
import { SummaryPage } from './pages/SummaryPage'
import { UsersPage } from './pages/UsersPage'
import { MyProfilePage } from './pages/MyProfilePage'
import { TodayPage } from './pages/TodayPage'
import { ReviewPage } from './pages/ReviewPage'
import { WeeklyReportPage } from './pages/WeeklyReportPage'
import { DirectoryPage } from './pages/DirectoryPage'
import { ShiftLogsPage } from './pages/ShiftLogsPage'

function Layout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <Outlet />
    </div>
  )
}

function HomePage() {
  const { user } = useAuth()
  if (user?.role === 'operator') {
    return <Navigate to="/today" replace />
  }
  if (user?.role === 'management') {
    return <Navigate to="/summary" replace />
  }
  return <Navigate to="/machines" replace />
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
          <Route path="/" element={<HomePage />} />
          <Route path="/machines" element={<MachineListPage />} />
          <Route path="/today" element={<TodayPage />} />
          <Route path="/machines/:id" element={<MachineDetailPage />} />
          <Route path="/profile" element={<MyProfilePage />} />
          <Route path="/directory" element={<DirectoryPage />} />
          <Route element={<RoleRoute roles={['admin', 'supervisor']} />}>
            <Route path="/review" element={<ReviewPage />} />
          </Route>
          <Route element={<RoleRoute roles={['admin', 'supervisor', 'management']} />}>
            <Route path="/shift" element={<ShiftLogsPage />} />
            <Route path="/overdue" element={<OverduePage />} />
            <Route path="/summary" element={<SummaryPage />} />
            <Route path="/reports" element={<WeeklyReportPage />} />
            <Route path="/users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <LocaleProvider>
        <AppRoutes />
      </LocaleProvider>
    </AuthProvider>
  )
}

export default App

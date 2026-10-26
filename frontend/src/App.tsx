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
import { SparesPage } from './pages/SparesPage'
import { RemovedPartsPage } from './pages/RemovedPartsPage'
import { SupervisorDashboard } from './pages/SupervisorDashboard'
import { BrandMark } from './components/BrandMark'
import { useLocale } from './locale/localeContext'

function Layout() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <NavBar />
      <div className="pb-24 lg:pb-0">
        <Outlet />
      </div>
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
  return <SupervisorDashboard />
}

function AppRoutes() {
  const { isLoading } = useAuth()
  const { t } = useLocale()

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-paper">
        <BrandMark />
        <p className="text-sm text-stone-500">{t.loading}</p>
      </div>
    )
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
            <Route path="/spares" element={<SparesPage />} />
            <Route path="/removed" element={<RemovedPartsPage />} />
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

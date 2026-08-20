import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { EditUserForm } from '../components/EditUserForm'

// Every role, including operator and management, can reach this page to
// edit their own name/phone (or email, for management)/WhatsApp number and
// change their own PIN or password -- just never their own role, which
// EditUserForm's isSelf mode enforces by not rendering that field at all
// (and the backend rejects it independently either way).
export function MyProfilePage() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  return (
    <div className="mx-auto max-w-md p-4">
      <h1 className="mb-4 text-xl font-semibold text-slate-900">My Profile</h1>
      <EditUserForm
        user={user}
        isSelf
        allowedRoles={[]}
        onSaved={() => {
          void refreshUser()
          navigate('/')
        }}
        onCancel={() => navigate('/')}
      />
    </div>
  )
}

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
    <div className="mx-auto w-full max-w-md px-4 pt-5 pb-6 sm:px-6 lg:pt-7">
      <h1 className="mb-4 text-2xl font-bold tracking-tight text-ink">My Profile</h1>
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

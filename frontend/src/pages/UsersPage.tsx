import { useState } from 'react'
import { useAsync } from '../lib/useAsync'
import { listUsers, deleteUser } from '../api/users'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'
import { CreateUserForm } from '../components/CreateUserForm'
import { EditUserForm } from '../components/EditUserForm'
import type { User } from '../api/types'

export function UsersPage() {
  const { user: currentUser } = useAuth()
  // GET /users is supervisor+management on the backend; operators only ever
  // see themselves via GET /auth/me, so this page has nothing to show them.
  const canView = currentUser?.role === 'supervisor' || currentUser?.role === 'management'
  const canManage = currentUser?.role === 'supervisor'

  const users = useAsync(() => (canView ? listUsers() : Promise.resolve([])), [canView])

  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  if (!canView) {
    return <p className="p-6 text-slate-500">User management is only available to supervisors and management.</p>
  }

  if (users.loading) return <p className="p-6 text-slate-500">Loading…</p>
  if (users.error) return <p className="p-6 text-red-600">{users.error}</p>
  if (!users.data) return null

  const userList = users.data

  async function handleDelete(target: User) {
    const confirmed = window.confirm(`Delete ${target.name}? This cannot be undone.`)
    if (!confirmed) return
    setDeleteError(null)
    setDeletingId(target.id)
    try {
      await deleteUser(target.id)
      await users.refetch()
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'Could not delete user')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-4 text-xl font-semibold text-slate-900">Users</h1>

      {canManage &&
        (creating ? (
          <CreateUserForm
            onCreated={() => {
              setCreating(false)
              void users.refetch()
            }}
            onCancel={() => setCreating(false)}
          />
        ) : (
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="mb-4 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            + Add user
          </button>
        ))}

      {deleteError && <p className="mb-2 text-sm text-red-600">{deleteError}</p>}

      <ul className="flex flex-col gap-2">
        {userList.map((u) => (
          <li key={u.id} className="rounded-md border border-slate-200 p-3">
            {editingId === u.id ? (
              <EditUserForm
                user={u}
                onSaved={() => {
                  setEditingId(null)
                  void users.refetch()
                }}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-slate-900">{u.name}</p>
                  <p className="text-sm text-slate-500">
                    {u.role} · {u.role === 'management' ? (u.email ?? '—') : (u.phoneNumber ?? '—')}
                    {u.whatsappNumber ? ` · WA ${u.whatsappNumber}` : ''}
                  </p>
                </div>
                {canManage && (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setEditingId(u.id)}
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(u)}
                      disabled={deletingId === u.id}
                      className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                    >
                      {deletingId === u.id ? 'Deleting…' : 'Delete'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

import { useState } from 'react'
import { useAsync } from '../lib/useAsync'
import { listVendorContacts, deleteVendorContact } from '../api/vendorContacts'
import { listMachines } from '../api/machines'
import { VendorContactForm } from '../components/VendorContactForm'
import { SPECIALTIES, specialtyLabel } from '../lib/specialty'
import { useAuth } from '../auth/useAuth'
import { useLocale } from '../locale/localeContext'
import { ApiError } from '../api/client'
import type { Machine, VendorContact } from '../api/types'

export function DirectoryPage() {
  const { user } = useAuth()
  const { locale, t } = useLocale()
  // Operators can read the list but never maintain it -- mirrors
  // backend/app/routers/contacts.py::_write_roles.
  const canEdit = user?.role === 'supervisor' || user?.role === 'admin'

  const contacts = useAsync(() => listVendorContacts(), [])
  const machines = useAsync(() => (canEdit ? listMachines() : Promise.resolve([] as Machine[])), [canEdit])

  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (contacts.loading) return <p className="p-6 text-slate-500">{t.loading}</p>
  if (contacts.error) return <p className="p-6 text-red-600">{contacts.error}</p>
  if (!contacts.data) return null

  const contactList = contacts.data
  const machineList = machines.data ?? []
  const machineName = new Map(machineList.map((m) => [m.id, m.name]))

  async function handleDelete(contact: VendorContact) {
    const confirmed = window.confirm(`Remove ${contact.name} from the help numbers?`)
    if (!confirmed) return
    setError(null)
    setDeletingId(contact.id)
    try {
      await deleteVendorContact(contact.id)
      contacts.refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete contact')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-4 pb-16">
      <h1 className="mb-1 text-2xl font-bold text-slate-900">{t.directory}</h1>
      <p className="mb-4 text-base text-slate-600">
        {locale === 'hi'
          ? 'मशीन में मैकेनिकल दिक्कत हो तो बाहर से इन्हें बुलाएँ।'
          : 'Outside people to call when something is mechanically wrong.'}
      </p>

      {canEdit && !creating && !editingId && (
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="mb-4 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          + Add contact
        </button>
      )}

      {canEdit && creating && (
        <VendorContactForm
          machines={machineList}
          onSaved={() => {
            setCreating(false)
            contacts.refetch()
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {contactList.length === 0 && (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-lg text-slate-600">{t.noContacts}</p>
      )}

      {SPECIALTIES.map((specialty) => {
        const group = contactList.filter((c) => c.specialty === specialty)
        if (group.length === 0) return null
        return (
          <section key={specialty} className="mb-6">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
              {specialtyLabel(specialty, locale)}
            </h2>
            <ul className="flex flex-col gap-3">
              {group.map((contact) =>
                editingId === contact.id ? (
                  <li key={contact.id}>
                    <VendorContactForm
                      contact={contact}
                      machines={machineList}
                      onSaved={() => {
                        setEditingId(null)
                        contacts.refetch()
                      }}
                      onCancel={() => setEditingId(null)}
                    />
                  </li>
                ) : (
                  <li key={contact.id} className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-lg font-semibold text-slate-900">{contact.name}</p>
                    <p className="text-sm text-slate-600">
                      {contact.company ?? '—'}
                      {' · '}
                      {contact.machineId ? (machineName.get(contact.machineId) ?? 'Machine') : t.allMachines}
                    </p>
                    {contact.notes && <p className="mt-1 text-sm text-slate-600">{contact.notes}</p>}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <a
                        href={`tel:${contact.phoneNumber}`}
                        className="min-h-12 flex-1 rounded-xl bg-slate-900 px-4 py-3 text-center text-lg font-semibold text-white"
                      >
                        {t.call} {contact.phoneNumber}
                      </a>
                      {contact.whatsappNumber && (
                        <a
                          href={`https://wa.me/${contact.whatsappNumber.replace(/\D/g, '')}`}
                          target="_blank"
                          rel="noreferrer"
                          className="min-h-12 rounded-xl border border-green-600 px-4 py-3 text-center text-base font-semibold text-green-700"
                        >
                          {t.whatsapp}
                        </a>
                      )}
                    </div>
                    {canEdit && (
                      <div className="mt-2 flex gap-2">
                        <button
                          type="button"
                          onClick={() => setEditingId(contact.id)}
                          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          disabled={deletingId === contact.id}
                          onClick={() => void handleDelete(contact)}
                          className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </li>
                ),
              )}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

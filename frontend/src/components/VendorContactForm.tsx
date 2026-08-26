import { useState } from 'react'
import type { FormEvent } from 'react'
import { createVendorContact, updateVendorContact } from '../api/vendorContacts'
import { ApiError } from '../api/client'
import { SPECIALTIES, specialtyLabel } from '../lib/specialty'
import { useLocale } from '../locale/localeContext'
import type { Machine, VendorContact, VendorSpecialty } from '../api/types'

export function VendorContactForm({
  contact,
  machines,
  onSaved,
  onCancel,
}: {
  contact?: VendorContact
  machines: Machine[]
  onSaved: () => void
  onCancel: () => void
}) {
  const { locale, t } = useLocale()
  const [name, setName] = useState(contact?.name ?? '')
  const [company, setCompany] = useState(contact?.company ?? '')
  const [specialty, setSpecialty] = useState<VendorSpecialty>(contact?.specialty ?? 'mechanical')
  const [phoneNumber, setPhoneNumber] = useState(contact?.phoneNumber ?? '')
  const [whatsappNumber, setWhatsappNumber] = useState(contact?.whatsappNumber ?? '')
  const [machineId, setMachineId] = useState(contact?.machineId ?? '')
  const [notes, setNotes] = useState(contact?.notes ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const payload = {
      name: name.trim(),
      company: company.trim() || null,
      specialty,
      phoneNumber: phoneNumber.trim(),
      whatsappNumber: whatsappNumber.trim() || null,
      machineId: machineId || null,
      notes: notes.trim() || null,
    }
    try {
      if (contact) {
        await updateVendorContact(contact.id, payload)
      } else {
        await createVendorContact(payload)
      }
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save contact')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="mb-4 flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4"
    >
      <p className="text-sm font-semibold text-slate-900">{contact ? 'Edit contact' : 'Add contact'}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Name</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Company ({t.optional})</span>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Specialty</span>
          <select
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value as VendorSpecialty)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base"
          >
            {SPECIALTIES.map((s) => (
              <option key={s} value={s}>
                {specialtyLabel(s, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Phone number</span>
          <input
            required
            inputMode="tel"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {t.whatsapp} ({t.optional})
          </span>
          <input
            inputMode="tel"
            value={whatsappNumber}
            onChange={(e) => setWhatsappNumber(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Machine</span>
          <select
            value={machineId}
            onChange={(e) => setMachineId(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base"
          >
            <option value="">{t.allMachines}</option>
            {machines.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Notes ({t.optional})</span>
        <textarea
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base"
        />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? t.saving : t.save}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          {t.cancel}
        </button>
      </div>
    </form>
  )
}

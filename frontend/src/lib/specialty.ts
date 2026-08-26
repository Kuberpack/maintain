import type { Locale } from './i18n'
import type { VendorSpecialty } from '../api/types'

export const SPECIALTIES: VendorSpecialty[] = ['mechanical', 'electrical', 'hydraulics', 'oem', 'other']

const LABELS: Record<VendorSpecialty, Record<Locale, string>> = {
  mechanical: { en: 'Mechanical', hi: 'मैकेनिकल' },
  electrical: { en: 'Electrical', hi: 'बिजली' },
  hydraulics: { en: 'Hydraulics / pneumatics', hi: 'हाइड्रोलिक / न्यूमैटिक' },
  oem: { en: 'Machine maker (OEM)', hi: 'मशीन कंपनी (OEM)' },
  other: { en: 'Other', hi: 'अन्य' },
}

export function specialtyLabel(specialty: VendorSpecialty, locale: Locale): string {
  return LABELS[specialty][locale]
}

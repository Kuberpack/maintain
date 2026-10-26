/** Spare counts are whole pieces: a bearing, a metre of belt, a packet. */

export function formatQty(qty: number): string {
  return String(qty)
}

/** '1' and '1.0' count. '1.001' and '3.999' do not. */
export function parseWholeQty(text: string): number | null {
  const trimmed = text.trim()
  if (!/^\d+(?:\.0+)?$/.test(trimmed)) return null
  const value = Number(trimmed)
  return Number.isSafeInteger(value) ? value : null
}

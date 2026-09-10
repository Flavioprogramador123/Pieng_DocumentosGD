/**
 * Bitola de cabo — formulário aceita "10" ou "10 mm²"; documentos sempre com unidade.
 */

export function formatBitolaMm2(value) {
  if (value == null || value === '') return ''
  const text = String(value).trim()
  if (!text) return ''
  const nums = text.match(/\d+(?:[.,]\d+)?/g)
  if (!nums?.length) return text
  let n = nums[0].replace(',', '.')
  if (n.endsWith('.0')) n = n.slice(0, -2)
  return `${n} mm²`
}

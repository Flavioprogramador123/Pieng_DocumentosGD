/** Tensão fase-neutro no formulário (127 V ou 220 V). V_LL vem do tipo de ligação. */

const UF_FN_DEFAULT = {
  GO: '220V',
  MA: '220V',
  PI: '220V',
  PA: '220V',
  SP: '220V',
  RJ: '127V',
  DEFAULT: '220V',
}

export function normalizeTensaoFaseNeutro(value, uf = 'GO') {
  const v = String(value || '').toUpperCase().replace(/\s/g, '')
  if (!v) return UF_FN_DEFAULT[uf?.toUpperCase()?.slice(0, 2)] || UF_FN_DEFAULT.DEFAULT
  if (v.includes('13.8') || v.includes('13800')) return '13.8kV'
  if (v.includes('127')) return '127V'
  if (v.includes('220') || v.includes('380')) return '220V'
  return String(value).trim()
}

export function suggestTensaoFaseNeutro(uf = 'GO') {
  return UF_FN_DEFAULT[uf?.toUpperCase()?.slice(0, 2)] || UF_FN_DEFAULT.DEFAULT
}

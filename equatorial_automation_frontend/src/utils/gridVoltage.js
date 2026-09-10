/** Tensão de atendimento no formulário — alinhada ao NT Equatorial: 127 V, 220 V, 380 V. */

const UF_FN_DEFAULT = {
  GO: '220V',
  MA: '220V',
  PI: '220V',
  PA: '220V',
  SP: '220V',
  RJ: '127V',
  DEFAULT: '220V',
}

/** Normaliza para 127V, 220V ou 380V (valores do NT). */
export function normalizeTensaoAtendimento(value, uf = 'GO') {
  const v = String(value || '').toUpperCase().replace(/\s/g, '')
  if (!v) return suggestTensaoAtendimento(uf)
  if (v.includes('127') && !v.includes('220') && !v.includes('380')) return '127V'
  if (v.includes('380') || v.includes('220/380') || (v.includes('220') && v.includes('380'))) return '380V'
  if (v.includes('13.8') || v.includes('13800')) return '220V'
  if (v.includes('220')) return '220V'
  return String(value).trim()
}

/** Sugere tensão conforme UF e tipo de ligação (trifásico → 380 V no NT). */
export function suggestTensaoAtendimento(uf = 'GO', tipoLigacao = 'MONOFASICO') {
  const tipo = String(tipoLigacao || '').toUpperCase()
  if (tipo.includes('TRIF')) return '380V'
  return UF_FN_DEFAULT[uf?.toUpperCase()?.slice(0, 2)] || UF_FN_DEFAULT.DEFAULT
}

/** @deprecated use normalizeTensaoAtendimento */
export const normalizeTensaoFaseNeutro = normalizeTensaoAtendimento

/** @deprecated use suggestTensaoAtendimento */
export const suggestTensaoFaseNeutro = (uf) => suggestTensaoAtendimento(uf)

/** Área unitária típica de módulo FV (m²) — igual backend/config_padrao.json */
export const DEFAULT_AREA_MODULO_M2 = 2.5

function parseNum(value) {
  if (value === null || value === undefined || value === '') return null
  const n = parseFloat(String(value).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

/** Área de um módulo em m² (catálogo, C×L ou padrão 2,5). */
export function moduleAreaM2(module) {
  const explicit = parseNum(module?.area_modulo)
  if (explicit != null && explicit > 0) return explicit

  const comp = parseNum(module?.comprimento_m)
  const larg = parseNum(module?.largura_m)
  if (comp != null && larg != null && comp > 0 && larg > 0) {
    return Math.round(comp * larg * 1000) / 1000
  }

  return DEFAULT_AREA_MODULO_M2
}

/** Soma qtd × área de cada linha de módulo. Retorna '' se nenhuma quantidade válida. */
export function computeAreaArranjo(modules) {
  let total = 0
  for (const m of modules || []) {
    const q = parseInt(String(m?.quantity ?? m?.quantidade ?? '').trim(), 10)
    if (!Number.isFinite(q) || q <= 0) continue
    total += q * moduleAreaM2(m)
  }
  if (total <= 0) return ''
  return String(Math.round(total * 1000) / 1000)
}

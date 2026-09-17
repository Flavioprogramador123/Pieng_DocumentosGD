/**
 * QDCA / distribuição de microinversores — sugestões no formulário.
 */

export function networkPhases(tipoLigacao = 'MONOFASICO') {
  const t = String(tipoLigacao || '').toUpperCase()
  if (t.includes('TRIF')) return { count: 3, labels: ['A', 'B', 'C'] }
  if (t.includes('BIF')) return { count: 2, labels: ['A', 'B'] }
  return { count: 1, labels: ['A'] }
}

export function suggestMicroPhaseCounts(totalMicros, tipoLigacao = 'TRIFASICO') {
  const n = Math.max(0, parseInt(String(totalMicros), 10) || 0)
  const { count, labels } = networkPhases(tipoLigacao)
  if (n === 0) return Object.fromEntries(labels.map((l) => [`qdca_micros_fase_${l.toLowerCase()}`, '']))
  const base = Math.floor(n / count)
  const extra = n % count
  const out = {}
  labels.forEach((label, i) => {
    out[`qdca_micros_fase_${label.toLowerCase()}`] = String(base + (i < extra ? 1 : 0))
  })
  return out
}

const STANDARD_BREAKERS = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 150, 200]

export function standardBreakerRating(amps) {
  const a = Number(amps)
  if (!Number.isFinite(a) || a <= 0) return 10
  for (const rating of STANDARD_BREAKERS) {
    if (rating >= a) return rating
  }
  return STANDARD_BREAKERS[STANDARD_BREAKERS.length - 1]
}

export function estimatePhaseNominalCurrentA(microsOnPhase, powerKwPerMicro, voltageLn = 220) {
  const q = parseInt(String(microsOnPhase), 10) || 0
  const p = parseFloat(String(powerKwPerMicro).replace(',', '.')) || 0
  if (q <= 0 || p <= 0) return ''
  const iMicro = (p * 1000) / voltageLn
  return (iMicro * q).toFixed(2).replace('.', ',')
}

/** Corrente de projeto na fase = nominal (P/V). O fator 1,25 é só para dimensionar o disjuntor. */
export function estimatePhaseProjectCurrentA(microsOnPhase, powerKwPerMicro, voltageLn = 220) {
  return estimatePhaseNominalCurrentA(microsOnPhase, powerKwPerMicro, voltageLn)
}

export function estimateInverterNominalCurrentA(powerKw, voltageLn = 220, trifasico = false, voltageLl = 380) {
  const p = parseFloat(String(powerKw).replace(',', '.')) || 0
  if (p <= 0) return ''
  const iNom = trifasico
    ? (p * 1000) / (voltageLl * Math.sqrt(3))
    : (p * 1000) / voltageLn
  return iNom.toFixed(2).replace('.', ',')
}

/** I projeto inversor = corrente nominal (sem ×1,25). */
export function estimateInverterProjectCurrentA(powerKw, voltageLn = 220, trifasico = false, voltageLl = 380) {
  return estimateInverterNominalCurrentA(powerKw, voltageLn, trifasico, voltageLl)
}

/** Disjuntor de acoplamento (DJG) — só quando há mais de um equipamento/inversor. */
export function shouldOfferCouplingBreaker(nInv) {
  return (parseInt(String(nInv), 10) || 0) > 1
}

/** 1 inversor mono: o disjuntor do equipamento já é o de acoplamento. */
export function isSingleInverterCoupling(nInv) {
  return (parseInt(String(nInv), 10) || 0) <= 1
}

export function estimatePhaseBreakerA(microsOnPhase, powerKwPerMicro, voltageLn = 220) {
  const q = parseInt(String(microsOnPhase), 10) || 0
  const p = parseFloat(String(powerKwPerMicro).replace(',', '.')) || 0
  if (q <= 0 || p <= 0) return ''
  const iMicro = (p * 1000) / voltageLn
  return String(standardBreakerRating(iMicro * q * 1.25))
}

export function sumPhaseMicros(technical, tipoLigacao) {
  const { labels } = networkPhases(tipoLigacao)
  return labels.reduce((acc, label) => {
    const v = parseInt(technical?.[`qdca_micros_fase_${label.toLowerCase()}`], 10)
    return acc + (Number.isFinite(v) ? v : 0)
  }, 0)
}

export function totalInverters(inverters = []) {
  return inverters.reduce((acc, inv) => acc + (parseInt(inv.quantity, 10) || 0), 0)
}

export function totalModules(modules = []) {
  return modules.reduce((acc, m) => acc + (parseInt(m.quantity, 10) || 0), 0)
}

export function inverterPowerKw(inverters = []) {
  const inv = inverters[0]
  if (!inv) return 0
  return parseFloat(String(inv.power || '').replace(',', '.')) || 0
}

export function suggestQdcaFields({ technical, client, modules, inverters }) {
  const tipoInv = String(technical?.tipo_inversor || 'STRING').toUpperCase()
  const tipoLig = client?.tipo_ligacao || 'MONOFASICO'
  const nInv = totalInverters(inverters)
  const pInv = inverterPowerKw(inverters)

  if (tipoInv.includes('MICRO')) {
    const phases = suggestMicroPhaseCounts(nInv, tipoLig)
    const { labels } = networkPhases(tipoLig)
    const bitola = technical?.bitola_cabo_ca || '6'
    const breakers = {}
    const bitolas = {}
    const correntes = {}
    labels.forEach((label) => {
      const key = `qdca_micros_fase_${label.toLowerCase()}`
      const micros = phases[key]
      if (micros) {
        const lb = label.toLowerCase()
        breakers[`qdca_disj_fase_${lb}`] = estimatePhaseBreakerA(micros, pInv)
        bitolas[`qdca_bitola_fase_${lb}`] = bitola
        correntes[`qdca_corrente_proj_fase_${lb}`] = estimatePhaseProjectCurrentA(micros, pInv)
      }
    })
    const disjWorst = Math.max(
      0,
      ...Object.values(breakers).map((v) => parseInt(String(v), 10) || 0),
    )
    return {
      ...phases,
      ...breakers,
      ...bitolas,
      ...correntes,
      ...(disjWorst > 0 ? { qdca_disjuntor_ca: String(disjWorst) } : {}),
      qdca_num_dps: String(labels.length),
      modulos_por_string: '1',
      strings_por_mppt: '1',
      qdca_tem_disj_acoplamento: shouldOfferCouplingBreaker(nInv) ? (technical?.qdca_tem_disj_acoplamento || '') : '0',
    }
  }

  const totalKw = pInv * Math.max(1, nInv)
  const disj = estimatePhaseBreakerA(1, totalKw, 220) || '32'
  const isTri = String(tipoLig).toUpperCase().includes('TRIF')
  const iProj = estimateInverterProjectCurrentA(pInv, 220, isTri && !tipoInv.includes('MICRO'), 380)
  return {
    qdca_disjuntor_ca: disj,
    qdca_bitola_ca: technical?.bitola_cabo_ca || '6',
    qdca_corrente_proj: iProj,
    qdca_num_dps: String(Math.max(1, nInv)),
    qdca_tem_disj_acoplamento: shouldOfferCouplingBreaker(nInv) ? (technical?.qdca_tem_disj_acoplamento || '') : '0',
  }
}

/** Preenche campos QDCA vazios com sugestão do backend (não sobrescreve edição manual). */
export function mergeSuggestedQdcaFields(prev = {}, suggested = {}) {
  if (!suggested || typeof suggested !== 'object') return {}
  const patch = {}
  for (const [key, value] of Object.entries(suggested)) {
    if (value == null || String(value).trim() === '') continue
    if (!prev[key] || String(prev[key]).trim() === '') {
      patch[key] = String(value)
    }
  }
  return patch
}

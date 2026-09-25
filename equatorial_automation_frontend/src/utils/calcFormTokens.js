/**
 * Mapeia tokens da aba Cálculos ↔ campos dos Dados Técnicos / Cliente.
 * Prioridade de exibição: override manual → valor do formulário → sugerido do motor.
 */

import { formatBitolaMm2 } from './bitola.js'

/** token → campo em technicalData (exceto casos especiais tratados em resolveFormTokenValue) */
export const TOKEN_TO_TECHNICAL = {
  DISJUNTOR_CA_INVERSOR_A: 'qdca_disjuntor_ca',
  BITOLA_CABO_CC: 'bitola_cabo_cc',
  BITOLA_CABO_CA: 'bitola_cabo_ca',
  BITOLA_CABO_PADRAO: 'bitola_cabo_padrao',
  BITOLA_TRONCO_QDCA: 'qdca_bitola_tronco',
  QDCA_DISJ_FASE_A: 'qdca_disj_fase_a',
  QDCA_DISJ_FASE_B: 'qdca_disj_fase_b',
  QDCA_DISJ_FASE_C: 'qdca_disj_fase_c',
  QDCA_MICROS_FASE_A: 'qdca_micros_fase_a',
  QDCA_MICROS_FASE_B: 'qdca_micros_fase_b',
  QDCA_MICROS_FASE_C: 'qdca_micros_fase_c',
  DISJUNTOR_GERAL_QDCA_A: 'qdca_disjuntor_geral',
  QTD_DPS_QDCA: 'qdca_num_dps',
  MODULOS_POR_STRING: 'modulos_por_string',
  STRINGS_POR_MPPT: 'strings_por_mppt',
  QTD_ENTRADAS_MPPT_INVERSOR: 'num_mppt',
  QDCA_CORRENTE_PROJ: 'qdca_corrente_proj',
  CURVA_ATUACAO_DISJUNTOR: 'curva_disjuntor',
  DISJUNTOR_ENTRADA: 'disjuntor_entrada',
}

function _digitsAmp(value) {
  const digits = String(value ?? '').replace(/[^\d.,]/g, '').replace(',', '.')
  return digits
}

function _normAmpDisplay(value) {
  const digits = _digitsAmp(value)
  return digits ? `${digits} A` : String(value ?? '').trim()
}

/**
 * Valor atual do formulário para um token (já formatado para a grade de cálculos).
 */
export function resolveFormTokenValue(token, technicalData = {}, clientData = {}) {
  if (!token) return ''

  if (token === 'TENSAO_ATENDIMENTO') {
    return String(clientData.tensao_atendimento || technicalData.tensao_atendimento || '').trim()
  }
  if (token === 'TIPO_REDE') {
    return String(clientData.tipo_ligacao || technicalData.tipo_ligacao || '').trim()
  }
  if (token === 'DISJUNTOR_ENTRADA') {
    const raw = technicalData.disjuntor_entrada || clientData.disjuntor_entrada
    return raw ? _normAmpDisplay(raw) : ''
  }
  if (token === 'BITOLA_CABO_CC') {
    return formatBitolaMm2(technicalData.bitola_cabo_cc)
  }
  if (token === 'BITOLA_CABO_CA') {
    return formatBitolaMm2(technicalData.qdca_bitola_ca || technicalData.bitola_cabo_ca)
  }
  if (token === 'BITOLA_CABO_PADRAO' || token === 'BITOLA_TRONCO_QDCA') {
    const key = token === 'BITOLA_CABO_PADRAO' ? 'bitola_cabo_padrao' : 'qdca_bitola_tronco'
    return formatBitolaMm2(technicalData[key])
  }
  if (token === 'DISJUNTOR_CA_INVERSOR_A') {
    const raw = technicalData.qdca_disjuntor_ca
      || technicalData.qdca_disj_fase_a
      || technicalData.qdca_disj_fase_b
      || technicalData.qdca_disj_fase_c
    return raw ? _normAmpDisplay(raw) : ''
  }
  if (token.endsWith('_A') && TOKEN_TO_TECHNICAL[token]) {
    const raw = technicalData[TOKEN_TO_TECHNICAL[token]]
    return raw ? _normAmpDisplay(raw) : ''
  }

  const key = TOKEN_TO_TECHNICAL[token]
  if (!key) return ''
  const raw = technicalData[key]
  return raw == null ? '' : String(raw).trim()
}

/**
 * Monta overrides iniciais a partir do formulário quando o valor difere do sugerido do motor.
 * Assim a grade já abre com o valor corrigido e persiste ao recalcular.
 */
export function seedTokenOverridesFromForm(calculations, technicalData, clientData) {
  const items = calculations?.all_items || []
  const next = {}
  for (const item of items) {
    const token = item?.token
    if (!token) continue
    const formVal = resolveFormTokenValue(token, technicalData, clientData)
    if (!formVal) continue
    const suggested = String(item.valor_sugerido ?? item.valor ?? '').trim()
    // Se o backend já priorizou o formulário, item.valor == formVal — ainda assim
    // marca override só quando há sugerido diferente (destaque âmbar).
    if (item.valor_sugerido && formVal !== String(item.valor_sugerido).trim()) {
      next[token] = formVal
      continue
    }
    if (suggested && formVal !== suggested && formVal !== String(item.valor ?? '').trim()) {
      next[token] = formVal
    }
  }
  return next
}

/**
 * Valor a exibir na célula editável.
 */
export function displayCalcTokenValue(item, overrides, technicalData, clientData) {
  const token = item?.token
  if (token && overrides && Object.prototype.hasOwnProperty.call(overrides, token)) {
    return overrides[token]
  }
  if (token) {
    const formVal = resolveFormTokenValue(token, technicalData, clientData)
    if (formVal) return formVal
  }
  return item?.valor ?? ''
}

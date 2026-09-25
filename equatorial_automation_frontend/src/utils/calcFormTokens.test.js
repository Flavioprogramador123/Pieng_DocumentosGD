/**
 * Prioridade formulário → cálculo sugerido na aba Cálculos.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  displayCalcTokenValue,
  resolveFormTokenValue,
  seedTokenOverridesFromForm,
} from './calcFormTokens.js'

test('resolveFormTokenValue usa bitola dos Dados Técnicos', () => {
  assert.equal(
    resolveFormTokenValue('BITOLA_CABO_CC', { bitola_cabo_cc: '6' }, {}),
    '6 mm²',
  )
  assert.equal(
    resolveFormTokenValue('BITOLA_CABO_CA', { bitola_cabo_ca: '10', qdca_bitola_ca: '' }, {}),
    '10 mm²',
  )
  assert.equal(
    resolveFormTokenValue('BITOLA_CABO_CA', { bitola_cabo_ca: '6', qdca_bitola_ca: '16' }, {}),
    '16 mm²',
  )
})

test('displayCalcTokenValue prefere formulário ao sugerido do motor', () => {
  const item = { token: 'BITOLA_CABO_CC', valor: '4 mm²', valor_sugerido: '4 mm²' }
  const shown = displayCalcTokenValue(item, {}, { bitola_cabo_cc: '6' }, {})
  assert.equal(shown, '6 mm²')
})

test('displayCalcTokenValue prefere override manual', () => {
  const item = { token: 'BITOLA_CABO_CC', valor: '4 mm²' }
  const shown = displayCalcTokenValue(
    item,
    { BITOLA_CABO_CC: '10 mm²' },
    { bitola_cabo_cc: '6' },
    {},
  )
  assert.equal(shown, '10 mm²')
})

test('seedTokenOverridesFromForm marca divergência formulário vs sugerido', () => {
  const calc = {
    all_items: [
      {
        token: 'BITOLA_CABO_CC',
        valor: '6 mm²',
        valor_sugerido: '4 mm²',
        fonte: 'formulario',
      },
    ],
  }
  const overrides = seedTokenOverridesFromForm(calc, { bitola_cabo_cc: '6' }, {})
  assert.equal(overrides.BITOLA_CABO_CC, '6 mm²')
})

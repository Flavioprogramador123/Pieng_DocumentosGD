import { describe, it, expect } from 'vitest'
import { computeAreaArranjo, moduleAreaM2, DEFAULT_AREA_MODULO_M2 } from './areaUtils.js'

describe('areaUtils', () => {
  it('usa 2,5 m² por módulo quando não há dimensões', () => {
    expect(moduleAreaM2({})).toBe(DEFAULT_AREA_MODULO_M2)
    expect(computeAreaArranjo([{ quantity: '50' }])).toBe('125')
  })

  it('calcula área a partir de comprimento × largura', () => {
    expect(moduleAreaM2({ comprimento_m: '2.278', largura_m: '1.134' })).toBeCloseTo(2.583, 3)
    expect(computeAreaArranjo([{ quantity: '8', comprimento_m: '2', largura_m: '1' }])).toBe('16')
  })

  it('soma várias linhas de módulo', () => {
    expect(
      computeAreaArranjo([
        { quantity: '32', area_modulo: '2.5' },
        { quantity: '8', area_modulo: '2.8' },
      ]),
    ).toBe('102.4')
  })
})

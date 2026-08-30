import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  latLonToUtm,
  utmToLatLon,
  resolveCoordinates,
  parseCoordinateText,
} from './coordinateUtils.js'

/** Pares auditados contra Google Earth (tolerância ~1 m). */
const AUDIT_PAIRS = [
  {
    name: 'Goiânia região 1',
    latitude: -16.306664,
    longitude: -48.913032,
    googleE: 722986.05,
    googleN: 8196002.05,
    fuso: '22S',
    maxDeltaM: 0.01,
  },
  {
    name: 'Goiânia região 2 (faixa L)',
    latitude: -15.879944,
    longitude: -49.007317,
    googleE: 713364.87,
    googleN: 8243329.38,
    fuso: '22S',
    maxDeltaM: 1.5,
  },
]

function deltaM(e1, n1, e2, n2) {
  return Math.hypot(e1 - e2, n1 - n2)
}

for (const pair of AUDIT_PAIRS) {
  test(`lat/lon → UTM — ${pair.name}`, () => {
    const utm = latLonToUtm(pair.latitude, pair.longitude)
    assert.equal(utm.label, pair.fuso)
    assert.ok(
      deltaM(utm.easting, utm.northing, pair.googleE, pair.googleN) <= pair.maxDeltaM,
      `desvio ${deltaM(utm.easting, utm.northing, pair.googleE, pair.googleN).toFixed(2)} m > ${pair.maxDeltaM} m`,
    )
  })

  test(`UTM → lat/lon — ${pair.name}`, () => {
    const [lat, lon] = utmToLatLon(pair.googleE, pair.googleN, 22, true)
    assert.ok(Math.abs(lat - pair.latitude) < 0.00001)
    assert.ok(Math.abs(lon - pair.longitude) < 0.00001)
  })

  test(`resolveCoordinates — ${pair.name}`, () => {
    const resolved = resolveCoordinates({
      latitude: pair.latitude,
      longitude: pair.longitude,
      fuso_utm: pair.fuso,
    })
    assert.equal(resolved.fuso_utm, pair.fuso)
    const e = Number(resolved.coordenada_utm_x)
    const n = Number(resolved.coordenada_utm_y)
    assert.ok(deltaM(e, n, pair.googleE, pair.googleN) <= pair.maxDeltaM)
  })
}

test('parseCoordinateText — Google Earth faixa L (UTM + graus)', () => {
  const raw = '22 L 713364.87 m E, 8243329.38 m S / -15.879944 -49.007317'
  const parsed = parseCoordinateText(raw)
  assert.equal(parsed.coordenada_utm_x, '713364.87')
  assert.equal(parsed.coordenada_utm_y, '8243329.38')
  assert.equal(parsed.fuso_utm, '22S')
  assert.equal(parsed.latitude, '-15.879944')
  assert.equal(parsed.longitude, '-49.007317')
})

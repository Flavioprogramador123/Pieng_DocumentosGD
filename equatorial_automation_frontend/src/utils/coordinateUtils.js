/**
 * Conversão UTM WGS84 ↔ graus decimais (espelha backend/coordinate_utils.py).
 */

const WGS84_A = 6378137.0
const WGS84_F = 1 / 298.257223563
const WGS84_E2 = WGS84_F * (2 - WGS84_F)
const WGS84_EP2 = WGS84_E2 / (1 - WGS84_E2)
const WGS84_K0 = 0.9996

function sf(val, fallback = null) {
  if (val == null || val === '') return fallback
  const n = Number(String(val).replace(',', '.').trim())
  return Number.isFinite(n) ? n : fallback
}

function fmtCoord(value, decimals = 6) {
  const s = value.toFixed(decimals).replace(/\.?0+$/, '')
  return s
}

export function zoneFromLongitude(lon) {
  return Math.floor((lon + 180) / 6) + 1
}

export function parseFusoUtm(text) {
  if (!text) return { zone: 22, southern: true, label: '22S' }
  const raw = String(text).trim().toUpperCase()
  const m = raw.match(/(\d{1,2})/)
  if (!m) return { zone: 22, southern: true, label: '22S' }
  const zone = Number(m[1])
  let southern = true
  if (/\bS\b/.test(raw) || raw.endsWith('S')) southern = true
  else if (/\bN\b/.test(raw) && !/\bS\b/.test(raw)) southern = false
  return { zone, southern, label: `${zone}${southern ? 'S' : 'N'}` }
}

export function utmToLatLon(easting, northing, zone, southern = true) {
  const x = easting - 500_000
  let y = northing
  if (southern) y -= 10_000_000

  const e = Math.sqrt(WGS84_E2)
  const e1 = (1 - Math.sqrt(1 - WGS84_E2)) / (1 + Math.sqrt(1 - WGS84_E2))
  const longOrigin = ((zone - 1) * 6 - 180 + 3) * (Math.PI / 180)

  const m = y / WGS84_K0
  const mu = m / (WGS84_A * (1 - WGS84_E2 / 4 - (3 * WGS84_E2 ** 2) / 64 - (5 * WGS84_E2 ** 3) / 256))

  let phi1 =
    mu +
    ((3 * e1) / 2 - (27 * e1 ** 3) / 32) * Math.sin(2 * mu) +
    ((21 * e1 ** 2) / 16 - (55 * e1 ** 4) / 32) * Math.sin(4 * mu) +
    ((151 * e1 ** 3) / 96) * Math.sin(6 * mu) +
    ((1097 * e1 ** 4) / 512) * Math.sin(8 * mu)

  const sinPhi = Math.sin(phi1)
  const cosPhi = Math.cos(phi1)
  const tanPhi = Math.tan(phi1)

  const n1 = WGS84_A / Math.sqrt(1 - WGS84_E2 * sinPhi ** 2)
  const t1 = tanPhi ** 2
  const c1 = WGS84_EP2 * cosPhi ** 2
  const r1 = (WGS84_A * (1 - WGS84_E2)) / (1 - WGS84_E2 * sinPhi ** 2) ** 1.5
  const d = x / (n1 * WGS84_K0)

  const latRad =
    phi1 -
    ((n1 * tanPhi) / r1) *
      (d ** 2 / 2 -
        ((5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * WGS84_EP2) * d ** 4) / 24 +
        ((61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * WGS84_EP2 - 3 * c1 ** 2) * d ** 6) / 720)

  const lonRad =
    longOrigin +
    (d - ((1 + 2 * t1 + c1) * d ** 3) / 6 + ((5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * WGS84_EP2 + 24 * t1 ** 2) * d ** 5) / 120) /
      cosPhi

  return [(latRad * 180) / Math.PI, (lonRad * 180) / Math.PI]
}

export function latLonToUtm(lat, lon, zone = null) {
  const z = zone ?? zoneFromLongitude(lon)
  const southern = lat < 0
  const phi = (lat * Math.PI) / 180
  const lam = (lon * Math.PI) / 180
  const longOrigin = ((z - 1) * 6 - 180 + 3) * (Math.PI / 180)

  const sinPhi = Math.sin(phi)
  const cosPhi = Math.cos(phi)
  const tanPhi = Math.tan(phi)
  const n = WGS84_A / Math.sqrt(1 - WGS84_E2 * sinPhi ** 2)
  const t = tanPhi ** 2
  const c = WGS84_EP2 * cosPhi ** 2
  const aVal = cosPhi * (lam - longOrigin)

  const m =
    WGS84_A *
    ((1 - WGS84_E2 / 4 - (3 * WGS84_E2 ** 2) / 64 - (5 * WGS84_E2 ** 3) / 256) * phi -
      ((3 * WGS84_E2) / 8 + (3 * WGS84_E2 ** 2) / 32 + (45 * WGS84_E2 ** 3) / 1024) * Math.sin(2 * phi) +
      ((15 * WGS84_E2 ** 2) / 256 + (45 * WGS84_E2 ** 3) / 1024) * Math.sin(4 * phi) -
      ((35 * WGS84_E2 ** 3) / 3072) * Math.sin(6 * phi))

  let easting =
    WGS84_K0 *
      n *
      (aVal + ((1 - t + c) * aVal ** 3) / 6 + ((5 - 18 * t + t ** 2 + 72 * c - 58 * WGS84_EP2) * aVal ** 5) / 120) +
    500_000

  let northing =
    WGS84_K0 *
    (m +
      n *
        tanPhi *
        (aVal ** 2 / 2 + ((5 - t + 9 * c + 4 * c ** 2) * aVal ** 4) / 24 + ((61 - 58 * t + t ** 2 + 600 * c - 330 * WGS84_EP2) * aVal ** 6) / 720))

  if (southern) northing += 10_000_000

  return { easting, northing, zone: z, southern, label: `${z}${southern ? 'S' : 'N'}` }
}

const GOOGLE_EARTH_RE =
  /(\d{1,2})\s*([A-HJ-NP-Z])\s+([\d.,]+)\s*m\s*E\s*,?\s+([\d.,]+)\s*m\s*([NS])(?:\s*\/?\s*(-?\d+[.,]\d+)\s*°?\s+(-?\d+[.,]\d+)\s*°?)?/i

const LATLON_RE = /(-?\d{1,2}[.,]\d+)\s*°?\s*[,/\s]\s*(-?\d{1,3}[.,]\d+)\s*°?/

const UTM_PAIR_RE = /([\d.,]+)\s*m\s*E.*?([\d.,]+)\s*m\s*([NS])/i

export function parseCoordinateText(text) {
  if (!text || !String(text).trim()) return {}

  const raw = String(text).trim()
  const out = {}

  let m = raw.match(GOOGLE_EARTH_RE)
  if (m) {
    const zone = Number(m[1])
    const band = m[2].toUpperCase()
    const southern = m[5].toUpperCase() === 'S' || band >= 'N'
    out.coordenada_utm_x = String(sf(m[3]))
    out.coordenada_utm_y = String(sf(m[4]))
    out.fuso_utm = `${zone}${southern ? 'S' : 'N'}`
    out.coordenadas_raw = raw
    if (m[6] && m[7]) {
      out.latitude = String(sf(m[6]))
      out.longitude = String(sf(m[7]))
    }
    return out
  }

  m = raw.match(LATLON_RE)
  if (m) {
    out.latitude = String(sf(m[1]))
    out.longitude = String(sf(m[2]))
    out.coordenadas_raw = raw
    return out
  }

  m = raw.match(UTM_PAIR_RE)
  if (m) {
    out.coordenada_utm_x = String(sf(m[1]))
    out.coordenada_utm_y = String(sf(m[2]))
    const southern = m[3].toUpperCase() === 'S'
    const zm = raw.match(/(\d{1,2})\s*[A-HJ-NP-Z]/i)
    if (zm) out.fuso_utm = `${Number(zm[1])}${southern ? 'S' : 'N'}`
    out.coordenadas_raw = raw
    return out
  }

  return {}
}

/**
 * Preenche campos faltantes convertendo UTM ↔ graus decimais.
 * Retorna campos do formulário (coordenada_utm_x, latitude, etc.).
 */
export function resolveCoordinates({
  utm_x: utmX,
  utm_y: utmY,
  fuso_utm: fusoUtm,
  latitude,
  longitude,
  raw_text: rawText,
} = {}) {
  const parsed = rawText ? parseCoordinateText(rawText) : {}

  let easting = sf(utmX) ?? sf(parsed.coordenada_utm_x)
  let northing = sf(utmY) ?? sf(parsed.coordenada_utm_y)
  let lat = sf(latitude) ?? sf(parsed.latitude)
  let lon = sf(longitude) ?? sf(parsed.longitude)

  let { zone, southern, label: fusoLabel } = parseFusoUtm(fusoUtm || parsed.fuso_utm)

  if (easting != null && northing != null && (lat == null || lon == null)) {
    ;[lat, lon] = utmToLatLon(easting, northing, zone, southern)
  }

  if (lat != null && lon != null && (easting == null || northing == null)) {
    const utm = latLonToUtm(lat, lon, zone)
    easting = utm.easting
    northing = utm.northing
    zone = utm.zone
    southern = utm.southern
    fusoLabel = utm.label
  }

  if (easting == null && northing == null && lat == null && lon == null) {
    return {}
  }

  const result = {}
  if (easting != null) result.coordenada_utm_x = fmtCoord(easting, 2)
  if (northing != null) result.coordenada_utm_y = fmtCoord(northing, 2)
  if (fusoLabel) result.fuso_utm = fusoLabel
  if (lat != null) result.latitude = fmtCoord(lat, 6)
  if (lon != null) result.longitude = fmtCoord(lon, 6)
  return result
}

/** Mescla patch no estado técnico e resolve coordenadas bidirecionalmente. */
export function syncTechnicalCoordinates(prev, patch = {}) {
  const merged = { ...prev, ...patch }
  const resolved = resolveCoordinates({
    utm_x: merged.coordenada_utm_x,
    utm_y: merged.coordenada_utm_y,
    fuso_utm: merged.fuso_utm,
    latitude: merged.latitude,
    longitude: merged.longitude,
    raw_text: merged.coordenadas_raw,
  })
  return { ...merged, ...resolved }
}

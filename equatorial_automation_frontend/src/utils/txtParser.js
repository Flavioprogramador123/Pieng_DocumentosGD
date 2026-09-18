// Parser De/Para de TXT — extrai dados de faturas, CNH e anotações livres.
// As chaves do mapa são normalizadas (sem acento, sem pontuação) na carga.

import { resolveCoordinates } from './coordinateUtils.js'

const FIELD_MAPPING_RAW = {
  'nome': 'client_name',
  'nome completo': 'client_name',
  'nome do cliente': 'client_name',
  'titular': 'client_name',
  'razao social': 'client_name',

  'cpf': 'cpf',
  'cnpj': 'cpf',
  'cpf cnpj': 'cpf',

  'rg': 'rg',
  'identidade': 'rg',
  'rg ssp': 'rg',

  'nome do representante': 'nome_representante',
  'nome do representante legal': 'nome_representante',
  'representante legal': 'nome_representante',
  'cpf do representante': 'cpf_representante',
  'cpf representante': 'cpf_representante',
  'rg do representante': 'rg_representante',
  'rg representante': 'rg_representante',

  'validade cnh': 'validade_cnh',
  'validade da cnh': 'validade_cnh',

  'data de nascimento': 'data_nascimento',
  'nascimento': 'data_nascimento',
  'dt nascimento': 'data_nascimento',
  'dt de nascimento': 'data_nascimento',

  'telefone': 'telefone',
  'telefone celular': 'telefone',
  'celular': 'telefone',
  'fone': 'telefone',
  'fone celular': 'telefone',
  'tel': 'telefone',
  'whatsapp': 'telefone',
  'whats': 'telefone',

  'email': 'email',
  'e mail': 'email',
  'correio eletronico': 'email',

  'logradouro': 'logradouro',
  'endereco': 'endereco_completo',
  'endereco completo': 'endereco_completo',

  'numero': 'numero',
  'numero do imovel': 'numero',

  'complemento': 'complemento',
  'compl': 'complemento',

  'bairro': 'bairro',

  'cidade': 'cidade',
  'municipio': 'cidade',

  'uf': 'uf',
  'estado': 'uf',

  'cidade uf': 'cidade_uf',
  'municipio uf': 'cidade_uf',
  'municipio estado': 'cidade_uf',

  'cep': 'cep',
  'codigo postal': 'cep',

  'unidade consumidora': 'consumer_unit',
  'unidade consumidora uc': 'consumer_unit',
  'uc': 'consumer_unit',
  'conta contrato': 'consumer_unit',
  'numero da uc': 'consumer_unit',
  'numero uc': 'consumer_unit',

  'tensao de atendimento': 'tensao_atendimento',
  'tensao de atendimento v': 'tensao_atendimento',
  'tensao da rede': 'tensao_atendimento',
  'padrao de conexao': 'padrao_conexao',
  'padrao de ligacao': 'padrao_conexao',
  'ligacao existente': 'padrao_conexao',

  'tipo de ligacao': 'tipo_ligacao',
  'conexao da rede': 'tipo_ligacao',

  'classe': 'classe',
  'tipo de consumo': 'classe',

  'disjuntor de entrada': 'disjuntor_entrada',
  'disjuntor de entrada a': 'disjuntor_entrada',
  'disjuntor geral': 'disjuntor_entrada',
  'disjuntor ca': 'disjuntor_entrada',
  'disjuntor ac': 'disjuntor_entrada',
  'disjuntor de protecao ac': 'disjuntor_entrada',
  'disjuntor de protecao': 'disjuntor_entrada',

  'curva do disjuntor': 'curva_disjuntor',
  'curva de atuacao': 'curva_disjuntor',

  'tipo dps': 'dps_tipo',
  'dps tipo': 'dps_tipo',
  'classe dps': 'dps_classe',
  'dps classe': 'dps_classe',

  'bitola cabo ca': 'bitola_cabo_ca',
  'bitola do cabo ca': 'bitola_cabo_ca',
  'secao cabo ca': 'bitola_cabo_ca',
  'cabeamento ac': 'bitola_cabo_ca',
  'cabeamento ca': 'bitola_cabo_ca',
  'cabo ac': 'bitola_cabo_ca',
  'cabo ca': 'bitola_cabo_ca',

  'bitola cabo cc': 'bitola_cabo_cc',
  'bitola do cabo cc': 'bitola_cabo_cc',
  'secao cabo cc': 'bitola_cabo_cc',

  'bitola cabo padrao': 'bitola_cabo_padrao',
  'bitola do cabo padrao': 'bitola_cabo_padrao',
  'bitola do cabo de entrada': 'bitola_cabo_padrao',

  'coordenada utm x': 'coordenada_utm_x',
  'coordenada x': 'coordenada_utm_x',
  'utm x': 'coordenada_utm_x',
  'coordenadas': 'coordenadas_raw',
  'coordenadas georreferenciadas': 'coordenadas_raw',
  'coordenada georreferenciada': 'coordenadas_raw',
  'latitude': 'latitude',
  'lat': 'latitude',
  'coordenada utm y': 'coordenada_utm_y',
  'coordenada y': 'coordenada_utm_y',
  'utm y': 'coordenada_utm_y',
  'longitude': 'longitude',
  'lng': 'longitude',
  'long': 'longitude',
  'fuso utm': 'fuso_utm',

  'n poste transformador': 'num_poste',
  'numero do poste': 'num_poste',
  'numero do poste transformador': 'num_poste',

  'tipo de arranjo': 'tipo_arranjo',
  'tipo de estrutura': 'tipo_arranjo',
  'tipo de estrutura arranjo': 'tipo_arranjo',
  'estrutura do arranjo': 'tipo_arranjo',

  'area dos arranjos': 'area_arranjo',
  'area dos arranjos m': 'area_arranjo',

  'data prevista de operacao': 'data_operacao',
  'data de operacao': 'data_operacao',
  'data inicio em operacao': 'data_operacao',
  'data início em operação': 'data_operacao',
  'data oper': 'data_operacao',
  'data do documento': 'data_documento',
  'data de assinatura': 'data_documento',

  'cidade do documento': 'cidade_documento',
  'cidade da assinatura': 'cidade_documento',

  'texto valor pagamento contrato': 'texto_valor_pagamento_contrato',
  'valor e forma de pagamento contrato': 'texto_valor_pagamento_contrato',
  'clausula valor pagamento contrato': 'texto_valor_pagamento_contrato',
  'texto pagamento': 'texto_valor_pagamento_contrato',
  'texto de pagamento': 'texto_valor_pagamento_contrato',
  'valor pagamento': 'texto_valor_pagamento_contrato',
  'pagamento contrato': 'texto_valor_pagamento_contrato',
  'clausula pagamento': 'texto_valor_pagamento_contrato',
  'clausula sexta': 'texto_valor_pagamento_contrato',

  'contrato': 'numero_contrato',
  'numero do contrato': 'numero_contrato',
  'número do contrato': 'numero_contrato',
  'n do contrato': 'numero_contrato',
  'no do contrato': 'numero_contrato',
  'contrato n': 'numero_contrato',

  'quantidade de modulos': 'qtd_modulos',
  'quantidade de paineis': 'qtd_modulos',
  'quantidade de placas': 'qtd_modulos',
  'qtd modulos': 'qtd_modulos',

  'modulos fotovoltaicos': 'equipamento_modulos',
  'paineis fotovoltaicos': 'equipamento_modulos',
  'placas fotovoltaicas': 'equipamento_modulos',

  'fabricante dos modulos': 'fabricante_modulo',
  'fabricante modulo': 'fabricante_modulo',

  'modelo dos modulos': 'modelo_modulo',
  'modelo dos paineis': 'modelo_modulo',
  'modelo do modulo': 'modelo_modulo',

  'potencia dos modulos': 'potencia_modulo',
  'potencia unitaria dos modulos': 'potencia_modulo',
  'potencia do modulo': 'potencia_modulo',
  'potencia dos paineis wp': 'potencia_modulo',
  'potencia dos paineis': 'potencia_modulo',
  'potencia unitaria dos modulos wp': 'potencia_modulo',

  'quantidade de inversores': 'qtd_inversores',
  'qtd inversores': 'qtd_inversores',

  'inversores': 'equipamento_inversores',
  'microinversores': 'equipamento_inversores',
  'micro inversores': 'equipamento_inversores',

  'fabricante dos inversores': 'fabricante_inversor',
  'fabricante inversor': 'fabricante_inversor',

  'modelo dos inversores': 'modelo_inversor',
  'modelo do inversor': 'modelo_inversor',
  'modelo dos microinversores': 'modelo_inversor',
  'modelo do microinversor': 'modelo_inversor',

  'potencia dos inversores': 'potencia_inversor',
  'potencia nominal dos inversores': 'potencia_inversor',
  'potencia do inversor': 'potencia_inversor',
  'potencia nominal dos inversores kw': 'potencia_inversor',
  'potencia do microinversor kw': 'potencia_inversor',
}

const FIELD_MAPPING = {}
for (const [key, field] of Object.entries(FIELD_MAPPING_RAW)) {
  FIELD_MAPPING[normalizeKey(key)] = field
}

const DATE_ONLY_RE = /^\d{1,2}[\/.\-]\d{1,2}[\/.\-]\d{2,4}$/
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/

export function normalizeKey(key) {
  return String(key || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

export function toIsoDate(value) {
  if (!value) return ''
  const raw = String(value).trim()
  if (ISO_DATE_RE.test(raw)) return raw
  const m = raw.match(/^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2,4})$/)
  if (!m) return raw
  const day = m[1].padStart(2, '0')
  const month = m[2].padStart(2, '0')
  let year = m[3]
  if (year.length === 2) year = Number(year) > 50 ? `19${year}` : `20${year}`
  return `${year}-${month}-${day}`
}

export function formatCpf(value) {
  const digits = String(value || '').replace(/\D/g, '')
  if (digits.length === 11) {
    return digits.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
  }
  if (digits.length === 14) {
    return digits.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
  }
  // Linhas com CPF repetido/duplicado (ex.: "426.985.961-04 / 42698596104"): usa o primeiro trecho.
  const first = String(value || '').split('/')[0].trim()
  const firstDigits = first.replace(/\D/g, '')
  if (firstDigits.length === 11) {
    return firstDigits.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
  }
  return first || String(value || '').trim()
}

export function formatCep(value) {
  const digits = String(value || '').replace(/\D/g, '')
  if (digits.length !== 8) return String(value || '').trim()
  return digits.replace(/(\d{5})(\d{3})/, '$1-$2')
}

/** Celular BR: 062991827090, 62991827090 → (62) 99182-7090 */
export function formatTelefone(value) {
  const raw = String(value || '').trim()
  let digits = raw.replace(/\D/g, '')
  if (!digits) return raw
  if (digits.startsWith('55') && digits.length >= 12) digits = digits.slice(2)
  while (digits.startsWith('0') && digits.length > 10) digits = digits.slice(1)
  if (digits.length === 11) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`
  }
  return raw
}

export function mapTensao(value, options = {}) {
  const raw = String(value || '')
  const v = raw.toUpperCase().replace(/\s/g, '')
  if (!v) return ''
  if (v.includes('127') && !v.includes('220') && !v.includes('380')) return '127V'
  if (v.includes('220/380') || v.includes('220380') || (v.includes('220') && v.includes('380'))) {
    return '380V'
  }
  const isTri = options.tri
    || mapLigacao(raw) === 'TRIFASICO'
    || /\bTRI\b/.test(raw.toUpperCase())
    || raw.toLowerCase().includes('trifas')
  if (v.includes('380') && isTri) return '380V'
  if (v.includes('380')) return '380V'
  if (v.includes('13.8') || v.includes('13800') || v.includes('13,8')) return '220V'
  if (v.includes('220')) return '220V'
  return raw.trim()
}

export function mapLigacao(value) {
  const v = normalizeKey(value)
  if (v.includes('trifas') || /\btri\b/.test(v)) return 'TRIFASICO'
  if (v.includes('bifas') || /\bbi\b/.test(v)) return 'BIFASICO'
  if (v.includes('monofas') || /\bmono\b/.test(v)) return 'MONOFASICO'
  return String(value || '').trim().toUpperCase()
}

export function mapClasse(value) {
  const v = normalizeKey(value)
  if (/\bb1\b/.test(v) || v.includes('convencional b1')) return 'RESIDENCIAL'
  if (v.includes('industr')) return 'INDUSTRIAL'
  if (v.includes('comerc')) return 'COMERCIAL'
  if (v.includes('rural')) return 'RURAL'
  if (v.includes('resid')) return 'RESIDENCIAL'
  return String(value || '').trim().toUpperCase()
}

function looksLikeDate(value) {
  return DATE_ONLY_RE.test(String(value || '').trim())
}

function looksLikeRg(value) {
  const v = String(value || '').trim()
  if (!v || looksLikeDate(v)) return false
  return /\d{5,}/.test(v.replace(/\D/g, '')) || /\d/.test(v)
}

function stripLineJunk(line) {
  return line
    .replace(/^[\s>*\-•●]+/, '')
    .replace(/^\*+\s*/, '')
    .replace(/\*+$/, '')
    .trim()
}

export function parseAddress(addressText) {
  const result = {}
  const raw = String(addressText || '').trim()
  if (!raw) return result

  const parts = raw.split(',').map((p) => p.trim()).filter(Boolean)
  if (parts.length === 0) return result

  const first = parts[0]
  const numeroMatch = first.match(/n[°ºo]?\s*(\d+[a-z0-9/-]*)/i)
    || raw.match(/,\s*n[°ºo]?\s*(\d+[a-z0-9/-]*)/i)

  if (numeroMatch) {
    result.numero = numeroMatch[1]
  }

  const streetMatch = first.match(/^((?:r(?:ua)?|av(?:enida)?|al(?:ameda)?|tv(?:essa)?|travessa|rod(?:ovia)?)\b.*)$/i)
  if (streetMatch) {
    result.logradouro = streetMatch[1]
      .replace(/n[°ºo]?\s*\d+[a-z0-9/-]*/i, '')
      .replace(/,+/g, ',')
      .trim()
      .replace(/[,\s]+$/, '')
  } else {
    result.logradouro = first.replace(/n[°ºo]?\s*\d+[a-z0-9/-]*/i, '').trim()
  }

  const rest = parts.slice(1).filter((p) => {
    if (numeroMatch && p.toLowerCase().includes(String(numeroMatch[0]).toLowerCase())) return false
    return true
  })

  if (rest.length) {
    result.complemento = rest.join(', ')
  }

  return result
}

function extractQuantity(text) {
  const match = String(text).match(/(\d+(?:[.,]\d+)?)\s*(?:unidades?|modulos?|paineis?|inversores?|placas?|micros?)/i)
  return match ? match[1].replace(',', '.') : null
}

function extractModulePower(text) {
  const match = String(text).match(/(\d+(?:[.,]\d+)?)\s*w(?:p)?\b/i)
  return match ? match[1].replace(',', '.') : null
}

function extractInverterPowerKw(text) {
  const raw = String(text)
  const kw = raw.match(/(\d+(?:[.,]\d+)?)\s*k\s*w\b/i)
  if (kw) return kw[1].replace(',', '.')
  const model = raw.match(/s(\d+[.,]\d+)\s*k\b/i)
  if (model) return model[1].replace(',', '.')
  return null
}

function extractMm2(text) {
  const match = String(text).match(/(\d+(?:[.,]\d+)?)\s*mm/i)
  return match ? match[1].replace(',', '.') : null
}

function extractAmperes(text) {
  const match = String(text).match(/(\d+(?:[.,]\d+)?)\s*a\b/i)
  return match ? match[1].replace(',', '.') : String(text).replace(/[^\d.,]/g, '')
}

function lookupField(normalizedKey) {
  if (FIELD_MAPPING[normalizedKey]) return FIELD_MAPPING[normalizedKey]

  const keys = Object.keys(FIELD_MAPPING).sort((a, b) => b.length - a.length)
  for (const key of keys) {
    if (normalizedKey === key) return FIELD_MAPPING[key]
    if (normalizedKey.startsWith(`${key} `) || normalizedKey.endsWith(` ${key}`)) {
      if (key.length >= 4 || ['uc', 'cpf', 'rg', 'cep', 'uf'].includes(key)) {
        return FIELD_MAPPING[key]
      }
    }
  }
  return null
}

function parseLineLabel(line) {
  const cleaned = stripLineJunk(line)
  if (!cleaned || !cleaned.includes(':')) return null

  const [rawKey, ...valueParts] = cleaned.split(':')
  const value = valueParts.join(':').trim()
  const normalizedKey = normalizeKey(rawKey)
  if (!normalizedKey) return null
  const mappedField = lookupField(normalizedKey)
  if (!mappedField) return null

  return {
    key: rawKey.trim(),
    normalizedKey,
    mappedField,
    value,
  }
}

function parseLine(line) {
  const parsed = parseLineLabel(line)
  if (!parsed || !parsed.value) return null
  return parsed
}

function isMultilineContractField(mappedField) {
  return mappedField === 'texto_valor_pagamento_contrato'
}

function readMultilineValue(lines, startIndex) {
  const parts = []
  let i = startIndex
  while (i < lines.length) {
    const next = parseLineLabel(lines[i])
    if (next?.mappedField) break
    const chunk = String(lines[i] || '').trim()
    if (chunk) parts.push(chunk)
    i += 1
  }
  return { value: parts.join('\n'), lastIndex: i - 1 }
}

function applyPadraoConexao(value, client) {
  const ligacao = mapLigacao(value)
  if (ligacao === 'TRIFASICO' || ligacao === 'BIFASICO' || ligacao === 'MONOFASICO') {
    client.tipo_ligacao = ligacao
  }
  const tensao = mapTensao(value, { tri: ligacao === 'TRIFASICO' })
  if (tensao) client.tensao_atendimento = tensao
  const classe = mapClasse(value)
  if (['RESIDENCIAL', 'COMERCIAL', 'INDUSTRIAL', 'RURAL'].includes(classe)) {
    client.classe = classe
  }
}

function parseGoogleEarthCoordinates(text) {
  if (!text) return null
  const raw = String(text).trim()

  const geo = raw.match(
    /(\d{1,2})\s*([A-HJ-NP-Z])\s+([\d.,]+)\s*m\s*E\s*,?\s+([\d.,]+)\s*m\s*([NS])(?:\s*\/\s*(-?\d+[.,]\d+)\s*°?\s+(-?\d+[.,]\d+)\s*°?)?/i,
  )
  if (geo) {
    const zone = geo[1]
    const southern = geo[5].toUpperCase() === 'S'
    const out = {
      coordenada_utm_x: geo[3].replace(',', '.'),
      coordenada_utm_y: geo[4].replace(',', '.'),
      fuso_utm: `${zone}${southern ? 'S' : 'N'}`,
      coordenadas_raw: raw,
    }
    if (geo[6] && geo[7]) {
      out.latitude = geo[6].replace(',', '.')
      out.longitude = geo[7].replace(',', '.')
    }
    return out
  }

  const latlon = raw.match(/(-?\d{1,2}[.,]\d+)\s*°?\s*[,/\s]\s*(-?\d{1,3}[.,]\d+)\s*°?/)
  if (latlon) {
    return {
      latitude: latlon[1].replace(',', '.'),
      longitude: latlon[2].replace(',', '.'),
      coordenadas_raw: raw,
    }
  }

  const utmPair = raw.match(/([\d.,]+)\s*m\s*E.*?([\d.,]+)\s*m\s*([NS])/i)
  if (utmPair) {
    const zoneMatch = raw.match(/(\d{1,2})\s*[A-HJ-NP-Z]/i)
    const southern = utmPair[3].toUpperCase() === 'S'
    const out = {
      coordenada_utm_x: utmPair[1].replace(',', '.'),
      coordenada_utm_y: utmPair[2].replace(',', '.'),
      coordenadas_raw: raw,
    }
    if (zoneMatch) out.fuso_utm = `${zoneMatch[1]}${southern ? 'S' : 'N'}`
    return out
  }

  return null
}

function applyCoordinates(parsed, technical) {
  if (!parsed) return
  for (const [key, val] of Object.entries(parsed)) {
    if (val != null && String(val).trim() !== '') {
      technical[key] = val
    }
  }
  const resolved = resolveCoordinates({
    utm_x: technical.coordenada_utm_x,
    utm_y: technical.coordenada_utm_y,
    fuso_utm: technical.fuso_utm,
    latitude: technical.latitude,
    longitude: technical.longitude,
    raw_text: technical.coordenadas_raw,
  })
  Object.assign(technical, resolved)
}

function harvestFromRawText(text, client, technical) {
  if (!client.cep) {
    const cep = text.match(/\bcep\b[:\s]*([0-9]{5}-?[0-9]{3})/i)
      || text.match(/\b([0-9]{5}-[0-9]{3})\b/)
    if (cep) client.cep = formatCep(cep[1])
  }

  if (!client.consumer_unit) {
    const uc = text.match(/unidade\s+consumidora(?:\s*\(uc\))?\s*:?\s*([0-9.\-]+)/i)
      || text.match(/\buc\b\s*:?\s*([0-9]{10,})/i)
    if (uc) client.consumer_unit = uc[1].replace(/[^\d]/g, '')
  }

  if (!technical.latitude || !technical.longitude) {
    const geo = text.match(/(-?\d{1,2}\.\d{3,})\s*°?\s*[,/\s]\s*(-?\d{1,3}\.\d{3,})\s*°?/)
      || text.match(/(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})/)
    if (geo) {
      technical.latitude = geo[1]
      technical.longitude = geo[2]
    }
  }

  if (!technical.coordenada_utm_x || !technical.coordenada_utm_y) {
    applyCoordinates(parseGoogleEarthCoordinates(text), technical)
  }

  if (!client.email) {
    const email = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)
    if (email) client.email = email[0]
  }

  if (!client.tipo_ligacao || !client.tensao_atendimento) {
    const ligacao = text.match(/ligac[aã]o\s+existente\s*:?\s*([^\n]+)/i)
    if (ligacao) applyPadraoConexao(ligacao[1].trim(), client)
  }

  if (!technical.disjuntor_entrada) {
    const disj = text.match(/disjuntor\s+de\s+prote[cç][aã]o\s+ac\s*:?\s*([^\n]+)/i)
    if (disj) {
      technical.disjuntor_entrada = extractAmperes(disj[1])
      const lig = mapLigacao(disj[1])
      if (lig === 'TRIFASICO' || lig === 'BIFASICO' || lig === 'MONOFASICO') {
        client.tipo_ligacao = lig
      }
    }
  }
}

function harvestContractFromRawText(text, contract) {
  if (!contract.numero_contrato) {
    const numero = text.match(/(?:^|\n)\s*contrato\s*:\s*(\d+\s*\/\s*\d{4})/im)
    if (numero) contract.numero_contrato = numero[1].replace(/\s+/g, '')
  }

  if (!contract.texto_valor_pagamento_contrato) {
    const bloco = text.match(
      /(?:^|\n)\s*(?:texto\s+(?:de\s+)?pagamento\s*:\s*)?(O investimento objeto deste contrato[\s\S]*?)(?=\n\s*[\wÀ-ú][^:\n]{0,40}:\s|\n\s*#\s|\n\s*\*\*|$)/im,
    )
    if (bloco) contract.texto_valor_pagamento_contrato = bloco[1].trim()
  }
}

function emptyEquipment() {
  return {
    modules: [{
      quantity: '', fabricante: '', model: '', power: '',
      voc: '', isc: '', vmpp: '', impp: '', eficiencia: '',
    }],
    inverters: [{
      quantity: '', fabricante: '', model: '', power: '',
      tensao_nominal: '', corrente_nominal: '', mppt_min: '', mppt_max: '', eficiencia: '',
    }],
  }
}

function finalizeEquipment(data) {
  return {
    quantity: data.quantity || '',
    fabricante: data.fabricante || '',
    model: data.model || '',
    power: data.power || '',
    voc: data.voc || '',
    isc: data.isc || '',
    vmpp: data.vmpp || '',
    impp: data.impp || '',
    eficiencia: data.eficiencia || '',
    tensao_nominal: data.tensao_nominal || '',
    corrente_nominal: data.corrente_nominal || '',
    mppt_min: data.mppt_min || '',
    mppt_max: data.mppt_max || '',
  }
}

export function parseTxtData(txtContent) {
  const raw = String(txtContent || '')
  const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)

  const client = {}
  const technical = {}
  const contract = {}
  const currentModuleData = {}
  const currentInverterData = {}

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    let parsed = parseLineLabel(line)
    if (!parsed) {
      const cleaned = stripLineJunk(line)
      const cepLoose = cleaned?.match(/^cep\s+(\d{5}-?\d{3})$/i)
      if (cepLoose) {
        parsed = { key: 'CEP', normalizedKey: 'cep', mappedField: 'cep', value: cepLoose[1] }
      } else {
        const phoneLoose = cleaned?.match(
          /^(?:fone|telefone|celular|tel|whatsapp|whats)\s*:?\s*(.+)$/i,
        )
        if (phoneLoose?.[1]?.trim()) {
          parsed = {
            key: 'Telefone',
            normalizedKey: 'telefone',
            mappedField: 'telefone',
            value: phoneLoose[1].trim(),
          }
        } else {
          continue
        }
      }
    }

    let { mappedField, value } = parsed
    if (isMultilineContractField(mappedField) && !value) {
      const block = readMultilineValue(lines, i + 1)
      value = block.value
      i = block.lastIndex
    }
    if (!value && !isMultilineContractField(mappedField)) continue

    if (mappedField === 'cidade_uf') {
      const match = value.match(/^(.+?)[\s/,-]+([A-Za-z]{2})$/)
      if (match) {
        client.cidade = match[1].trim()
        client.uf = match[2].toUpperCase()
      }
      continue
    }

    if (mappedField === 'endereco_completo') {
      Object.assign(client, parseAddress(value))
      continue
    }

    if (mappedField === 'padrao_conexao') {
      applyPadraoConexao(value, client)
      continue
    }

    if (mappedField === 'equipamento_modulos') {
      const qty = extractQuantity(value)
      const power = extractModulePower(value)
      if (qty) currentModuleData.quantity = qty
      if (power) currentModuleData.power = power
      currentModuleData.model = value.replace(/^\d+\s*unidades?\s+de\s+/i, '').trim()
      const fabricantes = [
        { token: 'RENEPV', label: 'RENE PV' },
        { token: 'RENE PV', label: 'RENE PV' },
        { token: 'JINKO', label: 'JINKO' },
        { token: 'CANADIAN', label: 'CANADIAN' },
        { token: 'TRINA', label: 'TRINA' },
        { token: 'JA SOLAR', label: 'JA SOLAR' },
        { token: 'LONGI', label: 'LONGI' },
        { token: 'TSUN', label: 'TSUN POWER' },
      ]
      const upper = value.toUpperCase()
      for (const fab of fabricantes) {
        if (upper.includes(fab.token.replace(/\s/g, '')) || upper.includes(fab.token)) {
          currentModuleData.fabricante = fab.label
          break
        }
      }
      continue
    }

    if (mappedField === 'equipamento_inversores') {
      const qty = extractQuantity(value)
      const power = extractInverterPowerKw(value)
      if (qty) currentInverterData.quantity = qty
      if (power) currentInverterData.power = power
      currentInverterData.model = value.replace(/^\d+\s*unidades?\s+de\s+/i, '').trim()
      const fabricantes = ['DEYE', 'GROWATT', 'FRONIUS', 'SOFAR', 'HUAWEI', 'SUNGROW']
      for (const fab of fabricantes) {
        if (value.toUpperCase().includes(fab)) {
          currentInverterData.fabricante = fab
          break
        }
      }
      const tensao = value.match(/(\d{3})\s*v\b/i)
      if (tensao) currentInverterData.tensao_nominal = tensao[1]
      continue
    }

    if (mappedField === 'coordenadas_raw') {
      applyCoordinates(parseGoogleEarthCoordinates(value), technical)
      continue
    }

    if (mappedField === 'cpf') {
      client.cpf = formatCpf(value)
      continue
    }

    if (mappedField === 'cpf_representante') {
      client.cpf_representante = formatCpf(value)
      continue
    }

    if (mappedField === 'rg') {
      if (looksLikeRg(value)) client.rg = value.replace(/\s+/g, ' ').trim()
      continue
    }

    if (mappedField === 'validade_cnh' || mappedField === 'data_nascimento') {
      const iso = toIsoDate(value)
      if (iso) client[mappedField] = iso
      continue
    }

    if (mappedField === 'data_operacao') {
      const iso = toIsoDate(value)
      if (iso) technical.data_operacao = iso
      continue
    }

    if (mappedField === 'data_documento') {
      const iso = toIsoDate(value)
      if (iso) contract.data_documento = iso
      continue
    }

    if (mappedField === 'cidade_documento') {
      contract.cidade_documento = value.trim()
      continue
    }

    if (mappedField === 'cep') {
      client.cep = formatCep(value)
      continue
    }

    if (mappedField === 'telefone') {
      client.telefone = formatTelefone(value)
      continue
    }

    if (mappedField === 'consumer_unit') {
      client.consumer_unit = value.replace(/[^\d]/g, '') || value.trim()
      continue
    }

    if (mappedField === 'tensao_atendimento') {
      client.tensao_atendimento = mapTensao(value) || value
      applyPadraoConexao(value, client)
      continue
    }

    if (mappedField === 'tipo_ligacao') {
      client.tipo_ligacao = mapLigacao(value)
      continue
    }

    if (mappedField === 'classe') {
      client.classe = mapClasse(value)
      continue
    }

    if (mappedField === 'disjuntor_entrada') {
      technical.disjuntor_entrada = extractAmperes(value)
      const lig = mapLigacao(value)
      if (lig === 'TRIFASICO' || lig === 'BIFASICO' || lig === 'MONOFASICO') {
        client.tipo_ligacao = lig
      }
      continue
    }

    if (mappedField === 'bitola_cabo_ca' || mappedField === 'bitola_cabo_cc' || mappedField === 'bitola_cabo_padrao') {
      technical[mappedField] = extractMm2(value) || value.replace(/[^\d.,]/g, '')
      if (mappedField === 'bitola_cabo_ca' && !technical.bitola_cabo_padrao) {
        technical.bitola_cabo_padrao = technical.bitola_cabo_ca
      }
      continue
    }

    const clientFields = [
      'client_name', 'email', 'logradouro', 'numero',
      'complemento', 'bairro', 'cidade', 'uf',
      'nome_representante', 'rg_representante',
    ]
    if (clientFields.includes(mappedField)) {
      client[mappedField] = mappedField === 'uf' ? value.toUpperCase().slice(0, 2) : value
      continue
    }

    if (mappedField === 'texto_valor_pagamento_contrato') {
      contract.texto_valor_pagamento_contrato = value.replace(/ \{\{NL\}\} /g, '\n')
      continue
    }

    if (mappedField === 'numero_contrato') {
      contract.numero_contrato = value.trim()
      continue
    }

    const technicalFields = [
      'curva_disjuntor', 'dps_tipo', 'dps_classe',
      'coordenada_utm_x', 'coordenada_utm_y', 'fuso_utm',
      'latitude', 'longitude', 'coordenadas_raw',
      'num_poste', 'tipo_arranjo', 'area_arranjo',
    ]
    if (technicalFields.includes(mappedField)) {
      technical[mappedField] = value
      continue
    }

    if (mappedField === 'qtd_modulos') {
      currentModuleData.quantity = extractQuantity(value) || value.replace(/[^\d]/g, '')
      continue
    }
    if (mappedField === 'fabricante_modulo') {
      currentModuleData.fabricante = value
      continue
    }
    if (mappedField === 'modelo_modulo') {
      currentModuleData.model = value
      continue
    }
    if (mappedField === 'potencia_modulo') {
      currentModuleData.power = extractModulePower(value) || value.replace(/[^\d.,]/g, '').replace(',', '.')
      continue
    }
    if (mappedField === 'qtd_inversores') {
      currentInverterData.quantity = extractQuantity(value) || value.replace(/[^\d]/g, '')
      continue
    }
    if (mappedField === 'fabricante_inversor') {
      currentInverterData.fabricante = value
      continue
    }
    if (mappedField === 'modelo_inversor') {
      currentInverterData.model = value
      continue
    }
    if (mappedField === 'potencia_inversor') {
      currentInverterData.power = extractInverterPowerKw(value) || value.replace(/[^\d.,]/g, '').replace(',', '.')
      continue
    }
  }

  harvestFromRawText(raw, client, technical)
  harvestContractFromRawText(raw, contract)

  if (client.uf) client.uf = String(client.uf).toUpperCase().slice(0, 2)

  const blanks = emptyEquipment()
  const modules = Object.keys(currentModuleData).length
    ? [{ ...blanks.modules[0], ...finalizeEquipment(currentModuleData) }]
    : blanks.modules
  const inverters = Object.keys(currentInverterData).length
    ? [{ ...blanks.inverters[0], ...finalizeEquipment(currentInverterData) }]
    : blanks.inverters

  return { client, technical, contract, modules, inverters }
}

export function fillGaps(base, incoming) {
  const out = { ...base }
  for (const [key, value] of Object.entries(incoming || {})) {
    const current = out[key]
    const empty = current === undefined || current === null || String(current).trim() === ''
    if (empty && value !== undefined && value !== null && String(value).trim() !== '') {
      out[key] = value
    }
  }
  return out
}

export function mergeFilled(base, incoming) {
  const out = { ...base }
  for (const [key, value] of Object.entries(incoming || {})) {
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      out[key] = value
    }
  }
  return out
}

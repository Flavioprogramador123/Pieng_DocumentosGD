/**

 * Preview local DE/PARA — funciona sem backend.

 * Espelha os rótulos enviados por create_txt_data() → tokens do gerador.

 */



function formatThdDht(value) {

  if (value == null || String(value).trim() === '') return '<3%'

  const text = String(value).trim()

  if (text.startsWith('<')) return text.includes('%') ? text : `${text}%`

  const n = parseFloat(text.replace(',', '.').replace(/[^\d.]/g, ''))

  if (!Number.isFinite(n) || n <= 3) return '<3%'

  return `≤${n}%`

}



function row(label, token, value, source = 'form') {

  const text = value == null ? '' : String(value)

  return {

    label,

    token,

    placeholder: `{{${token}}}`,

    value: text,

    filled: text.trim() !== '',

    source,

  }

}



export function buildLocalDeParaPreview(clientData, contractData, technicalData, modules, inverters) {

  const mappings = []

  const seen = new Set()

  const push = (...args) => {

    const r = row(...args)

    if (seen.has(r.token)) return

    seen.add(r.token)

    mappings.push(r)

  }



  push('Nome', 'NOME_CLIENTE', clientData.client_name)

  push('CPF', 'CPF', clientData.cpf)

  push('RG', 'RG_RAW', clientData.rg)

  push('Data de Nascimento', 'DATA_NASCIMENTO', clientData.data_nascimento)

  push('Telefone Celular', 'TELEFONE_CELULAR', clientData.telefone)

  push('E-mail', 'EMAIL', clientData.email)

  push('Endereço', 'ENDERECO', clientData.logradouro)

  if (clientData.logradouro) {
    const numero = (clientData.numero || '').trim() || 'S/N'
    push('Número', 'NUMERO', numero)
  }

  push('Complemento', 'COMPLEMENTO', clientData.complemento)

  push('Bairro', 'BAIRRO', clientData.bairro)

  push('Cidade', 'CIDADE', clientData.cidade)

  push('UF', 'UF', clientData.uf)

  push('CEP', 'CEP', clientData.cep)



  if (clientData.cidade && clientData.uf) {

    push('Cidade/UF', 'CIDADE_UF', `${clientData.cidade}/${clientData.uf}`)

  }



  const enderecoCompleto = [

    clientData.logradouro,

    clientData.logradouro
      ? `Nº ${(clientData.numero || '').trim() || 'S/N'}`
      : '',

    clientData.complemento,

    clientData.bairro,

    clientData.cidade && clientData.uf ? `${clientData.cidade}/${clientData.uf}` : '',

  ]

    .filter(Boolean)

    .join(', ')

  if (enderecoCompleto) {

    push('Endereço Completo', 'ENDERECO_COMPLETO', enderecoCompleto)

  }



  push('Unidade Consumidora (UC)', 'CONTA_CONTRATO', clientData.consumer_unit)

  push('Classe', 'CLASSE', clientData.classe)

  push('Tipo de Ligação', 'TIPO_LIGACAO', clientData.tipo_ligacao)

  const ligCaixa = String(clientData.tipo_ligacao || '').toUpperCase()
  const caixaVariante = ligCaixa.includes('TRIF') || ligCaixa.includes('BIF') ? 'polifásica' : 'monofásica'
  push('Texto Caixa de Medição', 'TEXTO_CAIXA', `(automático — ${caixaVariante})`)
  push('Figura Caixa de Medição', 'FIGURA_CAIXA', `(automático — ${caixaVariante})`)

  push('Tensão de Atendimento (V)', 'TENSAO_ATENDIMENTO', clientData.tensao_atendimento)

  push('Número do Contrato', 'NUMERO_CONTRATO', contractData.numero_contrato)

  push(

    'Texto Valor Pagamento Contrato',

    'TEXTO_VALOR_PAGAMENTO_CONTRATO',

    contractData.texto_valor_pagamento_contrato ? '(texto)' : '',

  )

  push('Data do Documento', 'DATA_DOCUMENTO', contractData.data_documento)

  push('Cidade do Documento', 'CIDADE_DOCUMENTO', contractData.cidade_documento || clientData.cidade)



  push('Disjuntor de Entrada (A)', 'DISJUNTOR_ENTRADA', technicalData.disjuntor_entrada)

  push('Nº Poste/Transformador', 'NUM_POSTE', technicalData.num_poste || 'ilégível')

  push('Coordenada UTM X', 'COORDENADA_UTM_X', technicalData.coordenada_utm_x)

  push('Coordenada UTM Y', 'COORDENADA_UTM_Y', technicalData.coordenada_utm_y)

  push('Fuso UTM', 'FUSO_UTM', technicalData.fuso_utm)

  push('Curva do Disjuntor', 'CURVA_ATUACAO_DISJUNTOR', technicalData.curva_disjuntor)

  push('Bitola Cabo CC', 'BITOLA_CABO_CC', technicalData.bitola_cabo_cc)

  push('Bitola Cabo CA', 'BITOLA_CABO_CA', technicalData.bitola_cabo_ca)

  push('Bitola Cabo Padrão', 'BITOLA_CABO_PADRAO', technicalData.bitola_cabo_padrao)

  push('Área dos Arranjos (m²)', 'AREA_ARRANJO', technicalData.area_arranjo)

  push('Tipo de Arranjo', 'TIPO_ARRANJO', technicalData.tipo_arranjo)

  push('Data Prevista de Operação', 'DATA_OPERACAO', technicalData.data_operacao)

  push('Demanda Alvo da Unidade (kW)', 'DEMANDA_ALVO_KW', technicalData.demanda_alvo_kw)

  push('Tabela de Demanda', 'TABELA_DEMANDA', technicalData.tabela_demanda_text ? '(texto)' : '')



  const mod = modules?.[0]

  if (mod) {

    push('Quantidade de Módulos', 'QTD_MODULOS', mod.quantity)

    push('Fabricante dos Módulos', 'FABRICANTE_MODULO', mod.fabricante)

    push('Modelo dos Módulos', 'MODELO_MODULO', mod.model)

    push('Potência Unitária dos Módulos (Wp)', 'POTENCIA_MODULO', mod.power)

    push('Tensão Voc [V]', 'TENSAO_CIRCUITO_ABERTO', mod.voc)

    push('Corrente Isc [A]', 'CORRENTE_CURTO_CIRCUITO', mod.isc)

    push('Tensão Vmpp [V]', 'TENSAO_MAX_POTENCIA', mod.vmpp)

    push('Corrente Impp [A]', 'CORRENTE_MAX_POTENCIA', mod.impp)

    push('Eficiência do Módulo (%)', 'EFICIENCIA_MODULO', mod.eficiencia)

  }



  const inv = inverters?.[0]

  if (inv) {

    push('Quantidade de Inversores', 'QTD_INVERSORES', inv.quantity)

    push('Fabricante dos Inversores', 'FABRICANTE_INVERSOR', inv.fabricante)

    push('Modelo dos Inversores', 'MODELO_INVERSOR', inv.model)

    push('Potência Nominal dos Inversores (kW)', 'POTENCIA_INVERSOR', inv.power)

    push('Tensão Nominal CA (V)', 'TENSAO_NOMINAL_CA_INVERSOR', inv.tensao_nominal)

    push('Mínima Tensão MPPT (V)', 'TENSAO_MPPT_MIN_INVERSOR', inv.mppt_min)

    push('Máxima Tensão MPPT (V)', 'TENSAO_MPPT_MAX_INVERSOR', inv.mppt_max)

    const thd = formatThdDht(inv.thd_pct)

    push('THD de Corrente (%)', 'THD_CORRENTE_INVERSOR', thd)

    push('DHT de Corrente (%)', 'DHT', thd)

  }



  const filled = mappings.filter((m) => m.filled).length

  return {

    mappings,

    derived_tokens: [],

    template_placeholders: mappings.map((m) => ({ ...m, in_templates: [] })),

    unresolved_by_template: {},

    stats: {

      form_fields: mappings.length,

      form_filled: filled,

      total_values: filled,

      template_tokens: mappings.length,

      template_filled: filled,

      template_pending: mappings.length - filled,

    },

    source: 'local',

  }

}



export function mergeDeParaPreview(local, remote) {

  if (!remote?.success && !remote?.mappings) return local

  return {

    ...remote,

    source: 'server',

    mappings: remote.mappings?.length ? remote.mappings : local.mappings,

  }

}


/** Valores padrão para instalações residenciais comuns */



export function todayIso() {

  return new Date().toISOString().slice(0, 10)

}



/** Data prevista de operação — padrão +20 dias a partir de hoje (ou data base). */

export function operacaoDefaultIso(fromDate = new Date()) {

  const d = new Date(fromDate)

  if (Number.isNaN(d.getTime())) return todayIso()

  d.setDate(d.getDate() + 20)

  return d.toISOString().slice(0, 10)

}


export const RESIDENTIAL_TECHNICAL_DEFAULTS = {

  disjuntor_entrada: '40',

  curva_disjuntor: 'C',

  dps_tipo: 'DPS Classe II',

  dps_classe: '275 V',

  bitola_cabo_ca: '6',

  bitola_cabo_cc: '4',

  bitola_cabo_padrao: '10',

  tipo_aterramento: 'Haste copper 2,4 m com caixa de inspeção',

  resistencia_aterramento: '≤ 10 Ω',

  fuso_utm: '22S',

  tipo_arranjo: 'Telhado inclinado',

  tipo_fonte: 'SOLAR FOTOVOLTAICA',

  dr_sensibilidade_ma: '30',

  dr_tipo: 'DR 30 mA — alta sensibilidade',

  data_operacao: operacaoDefaultIso(),

}



export function getInitialContractData() {

  return {

    numero_contrato: '',

    texto_valor_pagamento_contrato: '',

    data_documento: todayIso(),

    cidade_documento: '',

  }

}



export function getInitialTechnicalData() {

  return {

    ...RESIDENTIAL_TECHNICAL_DEFAULTS,

    coordenada_utm_x: '',

    coordenada_utm_y: '',

    coordenadas_raw: '',

    latitude: '',

    longitude: '',

    figura_map_zoom: '',

    num_poste: 'ilegível',

    area_arranjo: '',

    demanda_alvo_kw: '',

    demanda_notas: '',

    demanda_modelo_id: '',

    tabela_demanda_text: '',

    tabela_demanda_json: '',

    demand_table_ai: false,

    modulos_por_string: '',

    strings_por_mppt: '',

    micros_por_grupo_ca: '3',

    num_mppt: '2',

    tipo_inversor: 'STRING',

    qdca_micros_fase_a: '',
    qdca_micros_fase_b: '',
    qdca_micros_fase_c: '',
    qdca_disj_fase_a: '',
    qdca_disj_fase_b: '',
    qdca_disj_fase_c: '',
    qdca_disjuntor_ca: '',
    qdca_num_dps: '',
    qdca_observacoes: '',
    qdca_bitola_ca: '',
    qdca_bitola_fase_a: '',
    qdca_bitola_fase_b: '',
    qdca_bitola_fase_c: '',
    qdca_corrente_proj_fase_a: '',
    qdca_corrente_proj_fase_b: '',
    qdca_corrente_proj_fase_c: '',
    qdca_corrente_proj: '',
    qdca_corrente_proj_tronco: '',
    qdca_tem_disj_acoplamento: '0',
    qdca_disjuntor_geral: '',
    qdca_bitola_tronco: '10',

  }

}



export const EXEMPLO_TEXTO_VALOR_PAGAMENTO_CONTRATO = `• O investimento objeto deste contrato é de R$ 12.000,00.

- Pagos à vista na assinatura do contrato.

ou parcelados em 18 x R$ 804,00 no cartão de crédito.`

export const EXEMPLO_TEXTO_VALOR_PAGAMENTO_AVISTA = `• O investimento objeto deste contrato é de R$ 28.500,00.

- Pagamento integral à vista na assinatura do contrato, via PIX ou transferência bancária.`

export const EXEMPLO_TEXTO_VALOR_PAGAMENTO_ENTRADA = `• O investimento objeto deste contrato é de R$ 35.000,00.

- Entrada de 50% (R$ 17.500,00) na assinatura do contrato.

- Saldo em 12 parcelas de R$ 1.458,33, via boleto bancário.`

export const EXEMPLO_TEXTO_VALOR_PAGAMENTO_ENTRADA_MONTAGEM = `• O investimento objeto deste contrato é de R$ 24.000,00.

- Entrada de 70% na assinatura do contrato no valor de R$ 16.800,00.

- Restante no dia da montagem no valor de R$ 7.200,00.`

export const EXEMPLOS_TEXTO_VALOR_PAGAMENTO = [
  { id: 'cartao', label: 'R$ 12.000 / 18× cartão', texto: EXEMPLO_TEXTO_VALOR_PAGAMENTO_CONTRATO },
  { id: 'avista', label: 'R$ 28.500 à vista', texto: EXEMPLO_TEXTO_VALOR_PAGAMENTO_AVISTA },
  { id: 'entrada', label: 'R$ 35.000 / 50% + 12× boleto', texto: EXEMPLO_TEXTO_VALOR_PAGAMENTO_ENTRADA },
  { id: 'entrada_montagem', label: 'R$ 24.000 / 70% + montagem', texto: EXEMPLO_TEXTO_VALOR_PAGAMENTO_ENTRADA_MONTAGEM },
]



/** Compatibilidade: formulários JSON antigos guardavam contrato em technical. */

export function contractFromLegacyTechnical(technical = {}) {

  return {

    numero_contrato: technical.numero_contrato || '',

    texto_valor_pagamento_contrato: technical.texto_valor_pagamento_contrato || '',

    data_documento: technical.data_documento || todayIso(),

    cidade_documento: technical.cidade_documento || '',

  }

}


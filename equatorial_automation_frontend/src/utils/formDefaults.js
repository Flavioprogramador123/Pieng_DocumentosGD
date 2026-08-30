/** Valores padrão para instalações residenciais comuns */



export function todayIso() {

  return new Date().toISOString().slice(0, 10)

}



export const RESIDENTIAL_TECHNICAL_DEFAULTS = {

  disjuntor_entrada: '40',

  curva_disjuntor: 'C',

  dps_tipo: 'DPS Classe II',

  dps_classe: '275 V',

  bitola_cabo_ca: '6 mm²',

  bitola_cabo_cc: '4 mm²',

  bitola_cabo_padrao: '10 mm²',

  tipo_aterramento: 'Haste copper 2,4 m com caixa de inspeção',

  resistencia_aterramento: '≤ 10 Ω',

  fuso_utm: '22S',

  tipo_arranjo: 'Telhado inclinado',

  tipo_fonte: 'SOLAR FOTOVOLTAICA',

  dr_sensibilidade_ma: '30',

  dr_tipo: 'DR 30 mA — alta sensibilidade',

  data_operacao: todayIso(),

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

    num_poste: 'ilégível',

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

  }

}



export const EXEMPLO_TEXTO_VALOR_PAGAMENTO_CONTRATO = `• O investimento objeto deste contrato é de R$ 12.000,00.

- Pagos à vista na assinatura do contrato.

ou parcelados em 18 x R$ 804,00 no cartão de crédito.`



/** Compatibilidade: formulários JSON antigos guardavam contrato em technical. */

export function contractFromLegacyTechnical(technical = {}) {

  return {

    numero_contrato: technical.numero_contrato || '',

    texto_valor_pagamento_contrato: technical.texto_valor_pagamento_contrato || '',

    data_documento: technical.data_documento || todayIso(),

    cidade_documento: technical.cidade_documento || '',

  }

}


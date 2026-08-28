/** Valores padrão para instalações residenciais comuns */

export function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export const RESIDENTIAL_TECHNICAL_DEFAULTS = {
  disjuntor_entrada: '40',
  curva_disjuntor: 'C',
  dps_tipo: 'DPS Classe II',
  dps_classe: '275 V',
  bitola_cabo_ca: '10 mm²',
  bitola_cabo_cc: '6 mm²',
  bitola_cabo_padrao: '10 mm²',
  tipo_aterramento: 'Haste copper 2,4 m com caixa de inspeção',
  resistencia_aterramento: '≤ 10 Ω',
  fuso_utm: '22S',
  tipo_arranjo: 'Telhado inclinado',
  tipo_fonte: 'SOLAR FOTOVOLTAICA',
  dr_sensibilidade_ma: '30',
  dr_tipo: 'DR 30 mA — alta sensibilidade',
  data_documento: todayIso(),
  data_operacao: todayIso(),
}

export function getInitialTechnicalData() {
  return {
    ...RESIDENTIAL_TECHNICAL_DEFAULTS,
    coordenada_utm_x: '',
    coordenada_utm_y: '',
    latitude: '',
    longitude: '',
    num_poste: '',
    area_arranjo: '',
    demanda_alvo_kw: '',
    demanda_notas: '',
    tabela_demanda_text: '',
    demand_table_ai: false,
    modulos_por_string: '',
    num_mppt: '2',
    tipo_inversor: 'STRING',
  }
}

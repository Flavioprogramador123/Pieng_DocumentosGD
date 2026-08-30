"""
Normaliza payload do formulário web (campos planos) para a estrutura
aninhada esperada por create_txt_data() e gerar_documentos.py.
"""


def pick_field(item: dict | None, *keys, default=None):
    """Lê campo com aliases (frontend EN vs backend PT)."""
    if not isinstance(item, dict):
        return default
    for key in keys:
        val = item.get(key)
        if val not in (None, ''):
            return val
    return default


def _first(data, *keys, default=None):
    for key in keys:
        val = data.get(key)
        if val not in (None, ''):
            return val
    return default


def _normalize_module(module):
    if not isinstance(module, dict):
        return {}
    return {
        'quantidade': _first(module, 'quantidade', 'quantity'),
        'fabricante': _first(module, 'fabricante'),
        'modelo': _first(module, 'modelo', 'model'),
        'potencia': _first(module, 'potencia', 'power'),
        'voc': _first(module, 'voc'),
        'isc': _first(module, 'isc'),
        'vmpp': _first(module, 'vmpp'),
        'impp': _first(module, 'impp'),
        'eficiencia': _first(module, 'eficiencia', 'efficiency'),
        'comprimento_m': _first(module, 'comprimento_m'),
        'largura_m': _first(module, 'largura_m'),
        'area_modulo': _first(module, 'area_modulo'),
    }


def _normalize_inverter(inverter):
    if not isinstance(inverter, dict):
        return {}
    return {
        'quantidade': _first(inverter, 'quantidade', 'quantity'),
        'fabricante': _first(inverter, 'fabricante'),
        'modelo': _first(inverter, 'modelo', 'model'),
        'potencia': _first(inverter, 'potencia', 'power'),
        'tensao_nominal': _first(inverter, 'tensao_nominal'),
        'corrente_nominal': _first(inverter, 'corrente_nominal'),
        'mppt_min': _first(inverter, 'mppt_min'),
        'mppt_max': _first(inverter, 'mppt_max'),
        'eficiencia': _first(inverter, 'eficiencia', 'efficiency'),
        'thd_pct': _first(inverter, 'thd_pct', 'thd', 'dht'),
    }


def _flatten_web_payload(data: dict) -> dict:
    """App.jsx envia { client, technical, contract, modules, inverters } — achata para o mapper."""
    flat = dict(data)
    for section_key in ('client', 'technical', 'contract'):
        section = data.get(section_key)
        if isinstance(section, dict):
            for key, val in section.items():
                if flat.get(key) in (None, '') and val not in (None, ''):
                    flat[key] = val
    if flat.get('client_name') and not flat.get('nome'):
        flat['nome'] = flat['client_name']
    return flat


def normalize_form_payload(data):
    """
    Aceita payload plano (App.jsx) ou aninhado (TXT/IA).
    Retorna dict com cliente, unidade_consumidora, modulos, inversores, dados_tecnicos.
    """
    if not isinstance(data, dict):
        return {
            'cliente': {},
            'unidade_consumidora': {},
            'modulos': [],
            'inversores': [],
            'dados_tecnicos': {},
            'contrato': {},
        }

    data = _flatten_web_payload(data)

    cliente = dict(data.get('cliente') or {})
    uc = dict(data.get('unidade_consumidora') or {})
    tecnicos = dict(data.get('dados_tecnicos') or {})
    contrato = dict(data.get('contrato') or {})

    cliente_map = {
        'nome': ('client_name',),
        'cpf': ('cpf', 'client_cpf'),
        'rg': ('rg',),
        'data_nascimento': ('data_nascimento',),
        'telefone': ('telefone',),
        'email': ('email',),
        'endereco_completo': ('endereco_completo', 'client_address'),
        'logradouro': ('logradouro',),
        'numero': ('numero',),
        'complemento': ('complemento',),
        'bairro': ('bairro',),
        'cidade': ('cidade',),
        'uf': ('uf',),
        'cep': ('cep',),
    }
    for target, sources in cliente_map.items():
        if not cliente.get(target):
            val = _first(data, *sources)
            if val is not None:
                cliente[target] = val

    uc_map = {
        'numero': ('consumer_unit',),
        'classe': ('classe',),
        'tipo_ligacao': ('tipo_ligacao',),
        'tensao_atendimento': ('tensao_atendimento', 'grid_voltage'),
        'modalidade_compensacao': ('modalidade_compensacao',),
        'disjuntor_entrada': ('disjuntor_entrada',),
    }
    for target, sources in uc_map.items():
        if not uc.get(target):
            val = _first(data, *sources)
            if val is not None:
                uc[target] = val

    uc_extra = {
        'disjuntor_entrada': ('disjuntor_entrada',),
        'num_poste': ('num_poste',),
        'coordenada_utm_x': ('coordenada_utm_x',),
        'coordenada_utm_y': ('coordenada_utm_y',),
        'fuso_utm': ('fuso_utm',),
        'coordenadas_raw': ('coordenadas', 'coordenadas_raw'),
    }
    for target, sources in uc_extra.items():
        if not uc.get(target):
            val = _first(data, *sources)
            if val is not None:
                uc[target] = val

    tech_map = {
        'area_arranjo': ('area_arranjo',),
        'tipo_fonte': ('tipo_fonte',),
        'data_operacao': ('data_operacao',),
        'bitola_cabo_cc': ('bitola_cabo_cc',),
        'bitola_cabo_ca': ('bitola_cabo_ca',),
        'bitola_cabo_padrao': ('bitola_cabo_padrao',),
        'dps_cc': ('dps_tipo', 'dps_cc'),
        'dps_ca': ('dps_classe', 'dps_ca'),
        'aterramento': ('aterramento',),
        'tipo_aterramento': ('tipo_aterramento',),
        'resistencia_aterramento': ('resistencia_aterramento',),
        'disjuntor_curva': ('curva_disjuntor', 'disjuntor_curva'),
        'disjuntor_entrada': ('disjuntor_entrada',),
        'tipo_arranjo': ('tipo_arranjo',),
        'latitude': ('latitude',),
        'longitude': ('longitude',),
        'demanda_alvo_kw': ('demanda_alvo_kw',),
        'demanda_notas': ('demanda_notas',),
        'demanda_modelo_id': ('demanda_modelo_id',),
        'tabela_demanda_text': ('tabela_demanda_text',),
        'tabela_demanda_json': ('tabela_demanda_json',),
        'coordenadas_raw': ('coordenadas', 'coordenadas_raw'),
        'coordenada_utm_x': ('coordenada_utm_x',),
        'coordenada_utm_y': ('coordenada_utm_y',),
        'fuso_utm': ('fuso_utm',),
        'dr_sensibilidade_ma': ('dr_sensibilidade_ma',),
        'dr_tipo': ('dr_tipo',),
        'modulos_por_string': ('modulos_por_string',),
        'strings_por_mppt': ('strings_por_mppt',),
        'micros_por_grupo_ca': ('micros_por_grupo_ca',),
        'num_mppt': ('num_mppt',),
        'tipo_inversor': ('tipo_inversor',),
        'figura_map_zoom': ('figura_map_zoom',),
    }
    for target, sources in tech_map.items():
        if not tecnicos.get(target):
            val = _first(data, *sources)
            if val is not None:
                tecnicos[target] = val

    if tecnicos.get('tipo_aterramento') and tecnicos.get('resistencia_aterramento'):
        tecnicos.setdefault(
            'aterramento',
            f"{tecnicos['tipo_aterramento']} — {tecnicos['resistencia_aterramento']} Ω",
        )

    contrato_map = {
        'numero_contrato': ('numero_contrato',),
        'texto_valor_pagamento_contrato': ('texto_valor_pagamento_contrato',),
        'data_documento': ('data_documento',),
        'cidade_documento': ('cidade_documento',),
    }
    for target, sources in contrato_map.items():
        if not contrato.get(target):
            val = _first(data, *sources)
            if val is not None:
                contrato[target] = val

    raw_modulos = data.get('modulos') or data.get('modules') or []
    raw_inversores = data.get('inversores') or data.get('inverters') or []

    return {
        'cliente': cliente,
        'unidade_consumidora': uc,
        'modulos': [_normalize_module(m) for m in raw_modulos if m],
        'inversores': [_normalize_inverter(i) for i in raw_inversores if i],
        'dados_tecnicos': tecnicos,
        'contrato': contrato,
    }

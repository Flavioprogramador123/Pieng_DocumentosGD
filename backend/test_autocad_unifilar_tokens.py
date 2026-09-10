"""Teste: tokens unifilar CAD (micro, string, padrão de entrada)."""
import unittest

from autocad_tokens import enrich_autocad_values

SAMPLE_STRING = {
    'QTD_MODULOS': '10',
    'POTENCIA_MODULO': '700',
    'FABRICANTE_MODULO': 'RENEPV',
    'MODELO_MODULO': 'HJT 700W',
    'QTD_INVERSORES': '1',
    'FABRICANTE_INVERSOR': 'SAJ',
    'MODELO_INVERSOR': 'R5-S2',
    'POTENCIA_INVERSOR': '6',
    'POTENCIA_INVERSOR_UNITARIO': '6',
    'TIPO_INVERSOR': 'STRING',
    'TIPO_EQUIPAMENTO_INVERSOR': 'Inversor',
    'MODULOS_POR_STRING': '5',
    'TENSAO_CIRCUITO_ABERTO': '49.5',
    'CORRENTE_CURTO_CIRCUITO': '13.5',
    'TENSAO_MAX_POTENCIA': '41.2',
    'CORRENTE_MAX_POTENCIA': '12.8',
    'QTD_ENTRADAS_MPPT_INVERSOR': '2',
    'DISJUNTOR_ENTRADA': '40',
    'DISJUNTOR_CA_INVERSOR_A': '32',
    'BITOLA_CABO_PADRAO': '10 mm²',
    'BITOLA_CABO_CC': '4 mm²',
    'BITOLA_CABO_CA': '6 mm²',
    'TIPO_LIGACAO': 'MONOFASICO',
    'NUM_POSTE': 'ilegível',
}

SAMPLE_MICRO = {
    'QTD_MODULOS': '8',
    'POTENCIA_MODULO': '680',
    'FABRICANTE_MODULO': 'RENEPV',
    'MODELO_MODULO': 'RN-680WP',
    'QTD_INVERSORES': '2',
    'FABRICANTE_INVERSOR': 'DEYE',
    'MODELO_INVERSOR': 'SAJ-2.25KW',
    'POTENCIA_INVERSOR': '2.25',
    'POTENCIA_INVERSOR_UNITARIO': '2.25',
    'TIPO_INVERSOR': 'MICRO',
    'TIPO_EQUIPAMENTO_INVERSOR': 'Micro-Inversor',
    'DISJUNTOR_ENTRADA': '40',
    'BITOLA_CABO_PADRAO': '10 mm²',
    'BITOLA_CABO_CC': '4 mm²',
    'BITOLA_CABO_CA': '4 mm²',
    'TIPO_LIGACAO': 'MONOFASICO',
    'NUM_POSTE': 'ilegível',
}


class TestAutocadUnifilarTokens(unittest.TestCase):
    def test_string_inversor_layout(self):
        r = enrich_autocad_values(SAMPLE_STRING)
        self.assertIn('STRING 1', r['TEXTO_UNIFILAR_STRING_1'])
        self.assertIn('POT STRING: 3,5kWP', r['TEXTO_UNIFILAR_STRING_1'])
        self.assertNotIn('POT UNIT', r['TEXTO_UNIFILAR_STRING_1'])
        self.assertIn('POTÊNCIA NOMINAL CA: 6,0kW', r['TEXTO_UNIFILAR_INVERSOR'])
        self.assertIn('SAJ', r['TEXTO_UNIFILAR_INVERSOR'])
        self.assertIn('R5-S2', r['TEXTO_UNIFILAR_INVERSOR'])

    def test_micro_inversor_layout(self):
        r = enrich_autocad_values(SAMPLE_MICRO)
        self.assertIn('2 x Micro-Inversores marca DEYE', r['TEXTO_UNIFILAR_MICRO'])
        self.assertIn('SAJ-2.25KW', r['TEXTO_UNIFILAR_MICRO'])
        self.assertIn('potência pico AC 2,25 kW', r['TEXTO_UNIFILAR_MICRO'])
        self.assertIn('8 x PAINEIS RENEPV RN-680WP', r['TEXTO_UNIFILAR_ARRANJO_1'])
        self.assertIn('POT ARRANJO:5,44 kWP', r['TEXTO_UNIFILAR_ARRANJO_1'])
        self.assertIn('16#4mm² Borracha', r['TEXTO_CABO_CC_UNIFILAR'])

    def test_padrao_entrada(self):
        r = enrich_autocad_values(SAMPLE_STRING)
        self.assertIn('2#10 mm² -', r['TEXTO_CABO_PADRAO_UNIFILAR'])
        self.assertIn('PVC 70°C', r['TEXTO_CABO_PADRAO_UNIFILAR'])
        self.assertIn('Classe 2', r['TEXTO_CABO_PADRAO_UNIFILAR'])
        self.assertEqual(r['DISJUNTOR_CA_PADRAO_A'], '40')
        self.assertIn('ILÉGÍVEL', r['TEXTO_POSTE_UNIFILAR'])


if __name__ == '__main__':
    unittest.main()

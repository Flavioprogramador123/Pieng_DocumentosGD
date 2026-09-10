import unittest
from pathlib import Path

from gerar_documentos import build_values, load_defaults
from memorial_current_text import format_micro_qdca_memorial_currents

ROOT = Path(__file__).resolve().parents[1]


class TestMemorialCurrentText(unittest.TestCase):
    def test_micro_8_tri_formatted(self):
        qdca = {
            'current_per_micro_a': 10.23,
            'current_worst_phase_a': 30.68,
            'phase_details': [
                {'fase': 'A', 'micros': 3, 'breaker_a': 32, 'bitola_ca': '6', 'current_a': 30.68},
                {'fase': 'B', 'micros': 3, 'breaker_a': 32, 'bitola_ca': '6', 'current_a': 30.68},
                {'fase': 'C', 'micros': 2, 'breaker_a': 32, 'bitola_ca': '6', 'current_a': 20.45},
            ],
        }
        sistema, inversor, tensao = format_micro_qdca_memorial_currents(
            qdca,
            pot_inv_w=2250,
            voltage_ln_v=220,
            network_trifasico=True,
        )
        self.assertIn('I_micro =', sistema)
        self.assertIn('I_fase (pior caso)', sistema)
        self.assertIn('30,68 A', sistema)
        self.assertIn('Distribuição por fase no QDCA:', inversor)
        self.assertIn('• Fase A:', inversor)
        self.assertIn('cabo 6 mm²', inversor)
        self.assertIn('Corrente nominal por micro-inversor:', inversor)
        self.assertIn('trifásica', tensao)
        self.assertNotIn('QDCA com', tensao)

    def test_micro_suprime_soma_imax_vezes_qtd(self):
        """8 micros em 3 fases: não preencher Imáx × 8 nem corrente total agregada."""
        config = ROOT / 'backend' / 'config_padrao.json'
        raw = {
            'QTD_INVERSORES': '8',
            'POTENCIA_GERACAO': '18',
            'TIPO_INVERSOR': 'MICRO',
            'TIPO_LIGACAO': 'TRIFASICO',
            'TENSAO_ATENDIMENTO': '220',
            'CORRENTE_MAX_SAIDA_CA_INVERSOR': '10.3',
            'QDCA_MICROS_FASE_A': '3',
            'QDCA_MICROS_FASE_B': '3',
            'QDCA_MICROS_FASE_C': '2',
        }
        values = build_values(raw, load_defaults(config))
        self.assertEqual(values.get('CALCULO_CORRENTE_INVERSORES_TOTAL'), '')
        self.assertEqual(values.get('CALCULO_IMAX_CA'), '')
        self.assertEqual(values.get('CALCULO_CORRENTE_CA'), '')
        self.assertIn('I_fase (pior caso)', values.get('CALCULO_CORRENTE_SISTEMA', ''))


if __name__ == '__main__':
    unittest.main()

"""Testes — tabela de proteção CA (micro / string)."""
import unittest

from protection_hierarchy import (
    build_protection_table,
    format_protection_table_text,
    simulate_micro_scenarios,
    simulate_string_scenarios,
)
from qdca_layout import build_micro_qdca_layout, pack_micro_breaker_rows


class TestProtectionTable(unittest.TestCase):
    def test_2_micros_tri_economia_mesma_fase(self):
        rows = pack_micro_breaker_rows(2, network_type='trifasico', mode='economia')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['fase'], 'A')
        self.assertEqual(rows[0]['micros'], 2)

    def test_12kw_mono_dois_inversores_6kw(self):
        t = build_protection_table(
            topology='string',
            tipo_ligacao='MONOFASICO',
            power_kw_total=12,
            inverter_fase='monofasico',
        )
        eqs = t['usina']['equipamentos']
        self.assertEqual(len(eqs), 2)
        text = format_protection_table_text(t)
        self.assertIn('TABELA COMPARATIVA', text)
        self.assertIn('RAMAL DE ENTRADA', text)
        self.assertIsNone(t['usina'].get('acoplamento'))
        self.assertIn('Inversor string 1', text)
        self.assertIn('Inversor string 2', text)
        self.assertNotIn('tripolar', eqs[0].get('polos', ''))

    def test_tabela_colunas_padrao_e_usina(self):
        layout = build_micro_qdca_layout(
            num_micros=3, power_per_micro_w=2250, voltage_ln_v=220, network_type='monofasico',
        )
        from protection_hierarchy import enrich_micro_layout_protection
        layout = enrich_micro_layout_protection(layout, tipo_ligacao='MONOFASICO', num_micros=3)
        text = layout['protection_hierarchy']
        self.assertIn('Disjuntor', text)
        self.assertIn('Mono/Tri', text)
        self.assertIn('I máx.', text)
        self.assertIn('I projeto', text)
        self.assertIn('40 A monopolar', text)

    def test_string_tri_12kw_um_inversor(self):
        t = build_protection_table(
            topology='string',
            tipo_ligacao='TRIFASICO',
            power_kw_total=12,
            inverter_fase='trifasico',
        )
        self.assertEqual(len(t['usina']['equipamentos']), 1)
        self.assertIn('tripolar', t['usina']['equipamentos'][0]['polos'])

    def test_djg_quando_usuario_inclui(self):
        t = build_protection_table(
            topology='micro',
            tipo_ligacao='TRIFASICO',
            technical={'qdca_tem_disj_acoplamento': '1', 'qdca_disjuntor_geral': '50'},
            num_micros=8,
            power_per_micro_kw=2.25,
        )
        self.assertIsNotNone(t['usina']['acoplamento'])
        self.assertEqual(t['usina']['acoplamento']['disjuntor_a'], 50)

    def test_breaker_rows_respeitam_override_formulario(self):
        t = build_protection_table(
            topology='micro',
            tipo_ligacao='TRIFASICO',
            technical={
                'qdca_micros_fase_a': '3',
                'qdca_micros_fase_b': '3',
                'qdca_micros_fase_c': '2',
                'qdca_disj_fase_a': '32',
                'qdca_disj_fase_b': '32',
                'qdca_disj_fase_c': '32',
                'qdca_bitola_fase_a': '6',
            },
            num_micros=8,
            power_per_micro_kw=2.25,
        )
        self.assertTrue(t['breaker_rows'])
        for row in t['breaker_rows']:
            self.assertEqual(row['breaker_a'], 32)
        for eq in t['usina']['equipamentos']:
            self.assertEqual(eq['disjuntor_a'], 32)

    def test_simulations(self):
        self.assertEqual(len(simulate_micro_scenarios([2, 3, 4])), 6)
        self.assertEqual(len(simulate_string_scenarios([6, 10, 12])), 6)


if __name__ == '__main__':
    unittest.main()

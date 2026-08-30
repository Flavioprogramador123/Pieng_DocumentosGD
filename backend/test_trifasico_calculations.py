"""Cálculos trifásicos — PD e corrente de microinversores (caso 63 A / 4,5 kW)."""

import math
import unittest

from grid_voltage import resolve_ligacao_config
from nbr5410_calculations import calculate_ac_current_nbr5410, standard_breaker_rating
from normas_loader import calc_pd_max_kw


class TestTrifasicoCalculations(unittest.TestCase):
    def test_disjuntor_tripolar_trifasico(self):
        lig = resolve_ligacao_config('TRIFASICO')
        self.assertEqual(lig['num_polos_disjuntor'], '3')
        self.assertEqual(lig['descricao_polos'], 'Tripolar')

    def test_pd_trifasico_63a(self):
        pd_kw = calc_pd_max_kw('GO', 'TRIFASICO', 63)
        self.assertAlmostEqual(pd_kw, 38.254, places=2)
        kva = 220 * 63 * 3 / 1000
        self.assertAlmostEqual(kva, 41.58, places=2)
        self.assertAlmostEqual(kva * 0.92, pd_kw, places=2)

    def test_corrente_micro_trifasico_4_5kw(self):
        """2 × 2,25 kW micro monofásico em trifásico — I = P / 220 V."""
        result = calculate_ac_current_nbr5410(
            power_kw=4.5,
            voltage_v=380,
            system_type='trifasico',
            topology='micro',
            num_devices=2,
            voltage_ln_v=220,
        )
        self.assertAlmostEqual(result['current_total_a'], 20.45, places=1)
        self.assertAlmostEqual(result['current_per_phase_a'], 10.23, places=1)

    def test_disjuntor_qdca_25a_micro_trifasico(self):
        i_sys = 4500 / 220
        disj = standard_breaker_rating(i_sys * 1.25)
        self.assertEqual(disj, 25)

    def test_corrente_string_trifasico_usa_sqrt3(self):
        result = calculate_ac_current_nbr5410(
            power_kw=4.5,
            voltage_v=380,
            system_type='trifasico',
            topology='string',
            num_devices=1,
            voltage_ln_v=220,
        )
        expected = 4500 / (380 * math.sqrt(3))
        self.assertAlmostEqual(result['current_total_a'], expected, places=1)


if __name__ == '__main__':
    unittest.main()

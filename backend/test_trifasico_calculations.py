"""Cálculos trifásicos — PD e corrente de microinversores (caso 63 A / 4,5 kW)."""

import math
import unittest

from grid_voltage import resolve_ac_voltage, resolve_ligacao_config
from nbr5410_calculations import (
    calculate_ac_current_nbr5410,
    calculate_inverter_ac_current,
    validate_inverter_network_compatibility,
    standard_breaker_rating,
)
from normas_loader import calc_pd_max_kw


class TestTrifasicoCalculations(unittest.TestCase):
    def test_disjuntor_tripolar_trifasico(self):
        lig = resolve_ligacao_config('TRIFASICO')
        self.assertEqual(lig['num_polos_disjuntor'], '3')
        self.assertEqual(lig['descricao_polos'], 'Tripolar')

    def test_pd_trifasico_63a(self):
        pd_kw = calc_pd_max_kw('GO', 'TRIFASICO', 63)
        self.assertAlmostEqual(pd_kw, 38.148, places=2)
        kva = math.sqrt(3) * 380 * 63 / 1000
        self.assertAlmostEqual(kva, 41.465, places=2)
        self.assertAlmostEqual(kva * 0.92, pd_kw, places=2)

    def test_pd_monofasico_63a(self):
        """GO mono 63 A: P = V × I × FP ≈ 12,75 kW."""
        from normas_loader import calc_pd_kva_kw

        kva, pd_kw = calc_pd_kva_kw('GO', 'MONOFASICO', 63)
        self.assertAlmostEqual(pd_kw, 12.751, places=2)
        self.assertAlmostEqual(kva, 220 * 63 / 1000, places=3)

    def test_tensao_trifasico_220v_go(self):
        """220V único = VN; V_LL permanece 380 V em GO."""
        volt = resolve_ac_voltage('GO', 'TRIFASICO', '220V')
        self.assertAlmostEqual(volt['voltage_ln_v'], 220.0)
        self.assertAlmostEqual(volt['voltage_ll_v'], 380.0)
        self.assertAlmostEqual(volt['voltage_v'], 380.0)

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

    def test_corrente_string_mono_trifasico_6kw(self):
        """6 kW monofásico — I = 6000 / 220 = 27,27 A, disjuntor monopolar."""
        result = calculate_inverter_ac_current(
            power_kw=6.0,
            inverter_fase='monofasico',
            voltage_ln_v=220,
            voltage_ll_v=380,
            topology='string',
            num_devices=1,
        )
        self.assertAlmostEqual(result['current_nominal_a'], 6000 / 220, places=2)
        self.assertEqual(result['num_polos_disjuntor'], 1)
        self.assertIn('VN', result['formula'])

    def test_corrente_string_trifasico_usa_sqrt3(self):
        result = calculate_inverter_ac_current(
            power_kw=4.5,
            inverter_fase='trifasico',
            voltage_ln_v=220,
            voltage_ll_v=380,
            topology='string',
            num_devices=1,
        )
        expected = 4500 / (380 * math.sqrt(3))
        self.assertAlmostEqual(result['current_nominal_a'], expected, places=1)
        self.assertEqual(result['num_polos_disjuntor'], 3)

    def test_inversor_trifasico_rede_monofasica_erro(self):
        compat = validate_inverter_network_compatibility(
            'trifasico', 'monofasico', topology='string',
        )
        self.assertFalse(compat['compatible'])
        self.assertIn('não há como conectar', compat['message'].lower())


if __name__ == '__main__':
    unittest.main()

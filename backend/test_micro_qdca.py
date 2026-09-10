"""Microinversores trifásicos — QDCA por fase e disjuntor de entrada."""
import unittest

from nbr5410_calculations import calculate_micro_qdca_phases, distribute_micros_across_phases


class TestMicroQdca(unittest.TestCase):
    def test_distribui_8_micros_em_3_fases(self):
        self.assertEqual(distribute_micros_across_phases(8, 3), [3, 3, 2])

    def test_qdca_8_micros_2250w_tri(self):
        """8 × 2,25 kW em 220 V — fases 3+3+2, disj ~32 A na pior fase."""
        pot_micro_w = 2250.0
        qdca = calculate_micro_qdca_phases(8, pot_micro_w, 220.0, 'trifasico', 3)
        self.assertEqual(qdca['num_qdca_breakers'], 3)
        self.assertEqual(qdca['micros_per_phase'], [3, 3, 2])
        self.assertEqual(qdca['breaker_worst_a'], 40)  # 3×10,2 A × 1,25 → comercial 40 A
        self.assertLess(qdca['current_worst_phase_a'], 35)
        self.assertIn('Fase A: 3 micro', qdca['description'])
        self.assertNotIn('100', qdca['description'])

    def test_nao_soma_potencia_total_em_uma_fase(self):
        """Corrente pior fase deve ser << potência total / VN."""
        qdca = calculate_micro_qdca_phases(8, 2250.0, 220.0, 'trifasico', 3)
        i_errado_total = (8 * 2250) / 220
        self.assertLess(qdca['current_worst_phase_a'], i_errado_total / 2)


if __name__ == '__main__':
    unittest.main()

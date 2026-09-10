"""Fase CA do equipamento vs tipo de ligação da UC."""
import unittest

from grid_voltage import describe_equipment_ca_connection, resolve_equipment_fase_ca


class TestEquipmentFaseCa(unittest.TestCase):
    def test_micro_sempre_monofasico(self):
        self.assertEqual(resolve_equipment_fase_ca('MICRO', 'TRIFASICO'), 'monofasico')
        self.assertEqual(resolve_equipment_fase_ca('MICROINVERSOR', None), 'monofasico')

    def test_string_usa_catalogo(self):
        self.assertEqual(resolve_equipment_fase_ca('STRING', 'TRIFASICO'), 'trifasico')
        self.assertEqual(resolve_equipment_fase_ca('STRING', 'MONOFASICO'), 'monofasico')

    def test_micro_em_rede_tri_descricao(self):
        txt = describe_equipment_ca_connection(
            tipo_inversor='MICRO',
            fase_ca_catalog=None,
            voltage_ln_v=220,
            voltage_ll_v=380,
            tipo_ligacao_uc='TRIFASICO',
        )
        self.assertIn('Microinversor monofásico', txt)
        self.assertIn('Fase-Neutro', txt)
        self.assertIn('trifásica', txt.lower())
        self.assertNotIn('micro trifásico', txt.lower())


if __name__ == '__main__':
    unittest.main()

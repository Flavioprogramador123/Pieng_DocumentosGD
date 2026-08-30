"""Auditoria UTM ↔ graus decimais (pares validados no Google Earth)."""

import math
import unittest

from coordinate_utils import latlon_to_utm, utm_to_latlon, resolve_coordinates, parse_coordinate_text

AUDIT_PAIRS = [
    {
        'name': 'Goiânia região 1',
        'latitude': -16.306664,
        'longitude': -48.913032,
        'google_e': 722986.05,
        'google_n': 8196002.05,
        'fuso': '22S',
        'max_delta_m': 0.01,
    },
    {
        'name': 'Goiânia região 2 (faixa L)',
        'latitude': -15.879944,
        'longitude': -49.007317,
        'google_e': 713364.87,
        'google_n': 8243329.38,
        'fuso': '22S',
        'max_delta_m': 1.5,
    },
]


def _delta_m(e1, n1, e2, n2):
    return math.hypot(e1 - e2, n1 - n2)


class TestCoordinateUtils(unittest.TestCase):
    def test_parse_google_earth_faixa_l(self):
        raw = '22 L 713364.87 m E, 8243329.38 m S / -15.879944 -49.007317'
        parsed = parse_coordinate_text(raw)
        self.assertEqual(parsed['utm_x'], 713364.87)
        self.assertEqual(parsed['utm_y'], 8243329.38)
        self.assertEqual(parsed['fuso_utm'], '22S')
        self.assertEqual(parsed['latitude'], -15.879944)
        self.assertEqual(parsed['longitude'], -49.007317)

    @classmethod
    def _cases(cls):
        for pair in AUDIT_PAIRS:
            yield pair

    def test_latlon_to_utm_audit_pairs(self):
        for pair in self._cases():
            with self.subTest(pair=pair['name']):
                e, n, _zone, _southern, label = latlon_to_utm(
                    pair['latitude'], pair['longitude']
                )
                self.assertEqual(label, pair['fuso'])
                self.assertLessEqual(
                    _delta_m(e, n, pair['google_e'], pair['google_n']),
                    pair['max_delta_m'],
                )

    def test_utm_to_latlon_audit_pairs(self):
        for pair in self._cases():
            with self.subTest(pair=pair['name']):
                lat, lon = utm_to_latlon(pair['google_e'], pair['google_n'], 22, southern=True)
                self.assertAlmostEqual(lat, pair['latitude'], places=4)
                self.assertAlmostEqual(lon, pair['longitude'], places=4)

    def test_resolve_coordinates_audit_pairs(self):
        for pair in self._cases():
            with self.subTest(pair=pair['name']):
                resolved = resolve_coordinates(
                    latitude=pair['latitude'],
                    longitude=pair['longitude'],
                    fuso_utm=pair['fuso'],
                )
                e = float(resolved['coordenada_utm_x'])
                n = float(resolved['coordenada_utm_y'])
                self.assertEqual(resolved['fuso_utm'], pair['fuso'])
                self.assertLessEqual(
                    _delta_m(e, n, pair['google_e'], pair['google_n']),
                    pair['max_delta_m'],
                )


if __name__ == '__main__':
    unittest.main()

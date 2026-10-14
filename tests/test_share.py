import unittest
from atlas.share import canonical_path


class SharingRoutesTest(unittest.TestCase):
    def test_only_demo_reads_allowed(self):
        for path in ('/api/events', '/api/simulation/start', '/api/simulation/stop', '/api/operations?run_id=anything', '/api/summary?city_id=all', '/api/summary?source_kind=real', '/api/status?query=SELECT+1', '/api/summary?city_id=madrid&city_id=all'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                canonical_path(path)

    def test_parameters_canonicalized(self):
        self.assertEqual(canonical_path('/api/summary'), ('summary','/api/summary?city_id=madrid&source_kind=synthetic'))
        uid='12345678-1234-1234-1234-123456789012'
        kind,path=canonical_path('/api/track?run_id='+uid+'&courier_id='+uid)
        self.assertEqual(kind,'track')
        self.assertIn('courier_id='+uid,path)


if __name__ == '__main__':
    unittest.main()

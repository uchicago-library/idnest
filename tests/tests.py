import idnest
import unittest
import json

class IdnestTestCase(unittest.TestCase):
    def setUp(self):
        self.app = idnest.app.test_client()

    def tearDown(self):
        pass

    def test_ram_get_empty_root(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        rv = self.app.get("/")
        rb = rv.data.decode()
        rj = json.loads(rb)
        self.assertEqual(rv.status_code, 200)

    def test_ram_404_on_get_nonexistant_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        rv = self.app.get("/doesntexist/")
        self.assertEqual(rv.status_code, 404)

    def test_ram_mint_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        rv = self.app.post("/")
        self.assertEqual(rv.status_code, 200)
        rb = rv.data.decode()
        rj = json.loads(rb)
        self.assertIn(b"Minted", rv.data)

if __name__ == '__main__':
    unittest.main()

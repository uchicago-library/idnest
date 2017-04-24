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
        self.assertEqual(rv.status_code, 200)
        rt = rv.data.decode()
        rj = json.loads(rt)
        self.assertIn("Containers", rj)
        self.assertIsInstance(rj['Containers'], list)
        self.assertEqual(len(rj['Containers']), 0)

    def test_ram_404_on_get_nonexistant_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        rv = self.app.get("/doesntexist/")
        self.assertEqual(rv.status_code, 404)

    def test_ram_mint_a_single_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        rv = self.app.post("/")
        self.assertEqual(rv.status_code, 200)
        rt = rv.data.decode()
        rj = json.loads(rt)
        self.assertIn("Minted", rj)
        self.assertIsInstance(rj['Minted'], list)
        self.assertIn("_link", rj['Minted'][0])
        self.assertIn("identifier", rj['Minted'][0])

    def test_ram_mint_multiple_containers(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        rv = self.app.post("/", data={"num": 4})
        self.assertEqual(rv.status_code, 200)
        rt = rv.data.decode()
        rj = json.loads(rt)
        self.assertIn("Minted", rj)
        self.assertIsInstance(rj['Minted'], list)
        self.assertEqual(len(rj['Minted']), 4)
        for x in rj['Minted']:
            self.assertIn("_link", x)
            self.assertIn("identifier", x)

    def test_ram_add_member_to_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        prrv = self.app.post("/")
        self.assertEqual(prrv.status_code, 200)
        prrt = prrv.data.decode()
        prrj = json.loads(prrt)
        self.assertIn("Minted", prrj)
        self.assertIsInstance(prrj['Minted'], list)
        self.assertIn("_link", prrj['Minted'][0])
        self.assertIn("identifier", prrj['Minted'][0])
        container_id = prrj['Minted'][0]['identifier']
        gcrv = self.app.get("/{}/".format(container_id))
        self.assertEqual(gcrv.status_code, 200)
        gcrt = gcrv.data.decode()
        gcrj = json.loads(gcrt)
        self.assertIn("Members", gcrj)
        self.assertEqual(len(gcrj['Members']), 0)
        pcrv = self.app.post("/{}/".format(container_id), data={"member": "abc123"})
        self.assertEqual(pcrv.status_code, 200)


if __name__ == '__main__':
    unittest.main()

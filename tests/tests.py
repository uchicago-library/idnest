import idnest
import unittest
import json
from uuid import uuid4


class IdnestTestCase(unittest.TestCase):
    def setUp(self):
        self.app = idnest.app.test_client()

    def tearDown(self):
        pass

    def response_200_json(self, rv):
        self.assertEqual(rv.status_code, 200)
        rt = rv.data.decode()
        rj = json.loads(rt)
        return rj

    def get_root(self):
        rv = self.app.get("/")
        rj = self.response_200_json(rv)
        self.assertIn("Containers", rj)
        self.assertIsInstance(rj['Containers'], list)
        return rj

    def get_container(self, c_id):
        rv = self.app.get("/{}/".format(c_id))
        rj = self.response_200_json(rv)
        return rj

    def get_member(self, c_id, m_id):
        rv = self.app.get("/{}/{}".format(c_id, m_id))
        rj = self.response_200_json(rv)
        return rj

    def nonexistant_container_404s(self):
        rv = self.app.get("/{}/".format(uuid4().hex))
        self.assertEqual(rv.status_code, 404)

    def nonexistant_member_404s(self, c_id=None):
        if c_id is None:
            c_id = uuid4().hex
        rv = self.app.get("/{}/{}".format(c_id, uuid4().hex))
        self.assertEqual(rv.status_code, 404)

    def add_container(self):
        rv = self.app.post("/")
        rj = self.response_200_json(rv)
        self.assertIn("Minted", rj)
        self.assertIsInstance(rj['Minted'], list)
        self.assertIn("_link", rj['Minted'][0])
        self.assertIn("identifier", rj['Minted'][0])
        return rj['Minted'][0]['identifier']

    def add_multiple_containers(self, num=2):
        rv = self.app.post("/", data={"num": num})
        rj = self.response_200_json(rv)
        self.assertIn("Minted", rj)
        self.assertIsInstance(rj['Minted'], list)
        self.assertEqual(len(rj['Minted']), num)
        for x in rj['Minted']:
            self.assertIn("_link", x)
            self.assertIn("identifier", x)
        return [x['identifier'] for x in rj['Minted']]

    def add_member(self, c_id):
        pcrv = self.app.post("/{}/".format(c_id), data={"member": uuid4().hex})
        pcrj = self.response_200_json(pcrv)
        return pcrj['Added'][0]['identifier']

    def add_multiple_members(self, c_id):
        pass

    def test_ram_get_empty_root(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        rj = self.get_root()
        self.assertEqual(len(rj['Containers']), 0)

    def test_ram_404_on_get_nonexistant_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        self.nonexistant_container_404s()

    def test_ram_404_on_get_nonexistant_member(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        self.nonexistant_member_404s()

    def test_ram_404_on_get_nonexistant_member_in_container_that_exists(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        self.nonexistant_member_404s(c_id=self.add_container())

    def test_ram_mint_a_single_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        c_id = self.add_container()
        rj = self.get_root()
        self.assertIn("Containers", rj)
        self.assertEqual(len(rj['Containers']), 1)
        self.assertIn('identifier', rj['Containers'][0])
        self.assertEqual(rj['Containers'][0]['identifier'], c_id)
        self.get_container(c_id)

    def test_ram_mint_multiple_containers(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        ids = self.add_multiple_containers(20)
        rj = self.get_root()
        self.assertIn("Containers", rj)
        self.assertEqual(len(rj['Containers']), 20)
        for x in rj['Containers']:
            self.assertTrue(x['identifier'] in ids)

    def test_ram_add_member_to_container(self):
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)
        c_id = self.add_container()
        m_id = self.add_member(c_id)
        self.assertEqual(m_id, self.get_container(c_id)['Members'][0]['identifier'])
        self.get_member(c_id, m_id)


if __name__ == '__main__':
    unittest.main()

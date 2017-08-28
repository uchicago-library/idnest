import unittest
import json
from uuid import uuid4
from pymongo import MongoClient
from os import environ

environ['IDNEST_DEFER_CONFIG'] = "True"

import idnest


class RAMIdnestTestCase(unittest.TestCase):
    def setUp(self):
        idnest.app.config['TESTING'] = True
        self.app = idnest.app.test_client()
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RAMStorageBackend(idnest.blueprint)

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

    def remove_container(self, c_id):
        rv = self.app.delete("/{}/".format(c_id))
        rj = self.response_200_json(rv)
        self.assertIn("Deleted", rj)
        return rj

    def remove_member(self, c_id, m_id):
        rv = self.app.delete("/{}/{}".format(c_id, m_id))
        rj = self.response_200_json(rv)
        self.assertIn("Deleted", rj)
        return rj

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

    def test_get_empty_root(self):
        rj = self.get_root()
        self.assertEqual(len(rj['Containers']), 0)

    def test_404_on_get_nonexistant_container(self):
        self.nonexistant_container_404s()

    def test_404_on_get_nonexistant_member(self):
        self.nonexistant_member_404s()

    def test_404_on_get_nonexistant_member_in_container_that_exists(self):
        self.nonexistant_member_404s(c_id=self.add_container())

    def test_mint_a_single_container(self):
        c_id = self.add_container()
        rj = self.get_root()
        self.assertIn("Containers", rj)
        self.assertEqual(len(rj['Containers']), 1)
        self.assertIn('identifier', rj['Containers'][0])
        self.assertEqual(rj['Containers'][0]['identifier'], c_id)
        self.get_container(c_id)

    def test_mint_multiple_containers(self):
        ids = self.add_multiple_containers(20)
        rj = self.get_root()
        self.assertIn("Containers", rj)
        self.assertEqual(len(rj['Containers']), 20)
        for x in rj['Containers']:
            self.assertTrue(x['identifier'] in ids)

    def test_add_member_to_container(self):
        c_id = self.add_container()
        m_id = self.add_member(c_id)
        self.assertEqual(m_id, self.get_container(c_id)['Members'][0]['identifier'])
        self.get_member(c_id, m_id)

    def test_add_member_to_container_that_doesnt_exist_404s(self):
        c_id = uuid4().hex
        pcrv = self.app.post("/{}/".format(c_id), data={"member": uuid4().hex})
        self.assertEqual(pcrv.status_code, 404)

    def test_get_html_mint_page(self):
        rv = self.app.get("/mint")
        self.assertEqual(rv.status_code, 200)

    def test_get_html_member_add(self):
        rv = self.app.get("/{}/add".format(uuid4().hex))
        self.assertEqual(rv.status_code, 200)

    def test_removing_empty_container(self):
        c_id = self.add_container()
        self.remove_container(c_id)

    def test_removing_member(self):
        c_id = self.add_container()
        m_id = self.add_member(c_id)
        self.remove_member(c_id, m_id)

    def test_deleting_container_that_doesnt_exist_200s(self):
        rv = self.app.delete("/{}/".format(uuid4().hex))
        self.assertEqual(rv.status_code, 200)

    def test_deleting_a_nonexistant_member_from_an_existing_container(self):
        c_id = self.add_container()
        rv = self.app.delete("/{}/{}".format(c_id, uuid4().hex))
        self.assertEqual(rv.status_code, 200)

    def test_removing_popualted_container(self):
        c_id = self.add_container()
        self.add_member(c_id)
        self.remove_container(c_id)

    def test_container_limit_knockdown(self):
        rv = self.app.get("/", data={"limit": 1001})
        rj = self.response_200_json(rv)
        self.assertEqual(rj['pagination']['limit'], 1000)

    def test_member_limit_knockdown(self):
        c_id = self.add_container()
        m_ids = []
        for _ in range(20):
            m_ids.append(self.add_member(c_id))
        rv = self.app.get("/{}/".format(c_id), data={"limit": 1001})
        rj = self.response_200_json(rv)
        self.assertEqual(rj['pagination']['limit'], 1000)

    def test_containers_pagination_wrap(self):
        c_ids = []
        for _ in range(1234):
            c_ids.append(self.add_container())
        self.assertEqual(len(c_ids), len(set(c_ids)))
        self.assertEqual(len(c_ids), 1234)
        next_cursor = "0"
        comp_c_ids = []
        while next_cursor is not None:
            rv = self.app.get("/", data={"limit": 200, "cursor": next_cursor})
            rj = self.response_200_json(rv)
            next_cursor = rj['pagination']['next_cursor']
            for x in rj['Containers']:
                comp_c_ids.append(x['identifier'])
        self.assertEqual(len(c_ids), len(comp_c_ids))
        self.assertEqual(len(comp_c_ids), len(set(comp_c_ids)))
        for x in c_ids:
            self.assertIn(x, comp_c_ids)

    def test_members_pagination_wrap(self):
        c_id = self.add_container()
        m_ids = []
        for _ in range(1234):
            m_ids.append(self.add_member(c_id))
        self.assertEqual(len(m_ids), len(set(m_ids)))
        self.assertEqual(len(m_ids), 1234)
        next_cursor = "0"
        comp_m_ids = []
        while next_cursor is not None:
            rv = self.app.get("/{}/".format(c_id), data={"limit": 200, "cursor": next_cursor})
            rj = self.response_200_json(rv)
            next_cursor = rj['pagination']['next_cursor']
            for x in rj['Members']:
                comp_m_ids.append(x['identifier'])
        self.assertEqual(len(m_ids), len(comp_m_ids))
        self.assertEqual(len(comp_m_ids), len(set(comp_m_ids)))
        for x in m_ids:
            self.assertIn(x, comp_m_ids)

    def test_outside_pagination_range_containers(self):
        rv = self.app.get("/", data={"offset": 1001})
        rj = self.response_200_json(rv)

    def test_outside_pagination_range_members(self):
        pass

    def test_version(self):
        rv = self.app.get("/version")
        rj = self.response_200_json(rv)
        self.assertEqual(rj['version'], idnest.blueprint.__version__)


class MongoIdnestTestCase(RAMIdnestTestCase):
    def setUp(self):
        self.app = idnest.app.test_client()
        idnest.blueprint.BLUEPRINT.config['MONGO_HOST'] = "localhost"
        idnest.blueprint.BLUEPRINT.config['MONGO_DB'] = "test"
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.MongoStorageBackend(idnest.blueprint.BLUEPRINT)

    def tearDown(self):
        c = MongoClient(idnest.blueprint.BLUEPRINT.config['MONGO_HOST'],
                        idnest.blueprint.BLUEPRINT.config.get('MONGO_PORT', 27017))
        c.drop_database(idnest.blueprint.BLUEPRINT.config['MONGO_DB'])
        idnest.blueprint.BLUEPRINT.config['storage']


class RedisIdnestTestCase(RAMIdnestTestCase):
    def setUp(self):
        self.app = idnest.app.test_client()
        idnest.blueprint.BLUEPRINT.config['REDIS_HOST'] = "localhost"
        idnest.blueprint.BLUEPRINT.config['REDIS_DB'] = 0
        idnest.blueprint.BLUEPRINT.config['storage'] = idnest.blueprint.RedisStorageBackend(idnest.blueprint.BLUEPRINT)

    def tearDown(self):
        idnest.blueprint.BLUEPRINT.config['storage'].r.flushdb()


class ImproperSetupTestCase(unittest.TestCase):
    def test_no_storage_backend(self):
        self.app = idnest.app.test_client()
        rv = self.app.get("/")
        self.assertEqual(rv.status_code, 500)


if __name__ == '__main__':
    unittest.main()

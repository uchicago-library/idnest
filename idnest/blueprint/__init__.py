from uuid import uuid4
from abc import ABCMeta, abstractmethod

from flask import Blueprint, abort
from flask_restful import Resource, Api, reqparse
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId


BLUEPRINT = Blueprint('idnest', __name__)


BLUEPRINT.config = {
    'STORAGE_BACKEND': "RAM",  # Default to just using dicts/sets
    'MONGO_HOST': 'localhost',        # If the app says to use mongo
    'MONGO_PORT': 27017,              # but specifies no other relevant info
    'MONGO_DB': "tmp_"+uuid4().hex,   # then use sensible defaults
}


API = Api(BLUEPRINT)


class IStorageBackend(metaclass=ABCMeta):
    """
    _Abstracts_

    * mint_container
    * rm_container
    * ls_containers
    * add_member
    * rm_member
    * ls_members

    _Provided Convenience_
    (Over-ride these if there is a faster way to do it in your implementation)

    * mint_containers
    * rm_containers
    * container_exists
    * add_members
    * rm_members
    * member_exists
    """
    @classmethod
    @abstractmethod
    def mint_container(cls):
        pass

    @classmethod
    def mint_containers(cls, num):
        return [cls.mint_container() for _ in range(num)]

    @classmethod
    @abstractmethod
    def rm_container(cls, c_id):
        pass

    @classmethod
    def rm_containers(cls, c_ids):
        return [cls.rm_container(c_id) for c_id in c_ids]

    @classmethod
    @abstractmethod
    def ls_containers(cls):
        pass

    @classmethod
    def container_exists(cls, qc_id):
        return qc_id in cls.ls_containers()

    @classmethod
    @abstractmethod
    def add_member(cls, c_id, m_id):
        pass

    @classmethod
    def add_members(cls, c_id, m_ids):
        return [cls.add_member(c_id, m_id) for m_id in m_ids]

    @classmethod
    @abstractmethod
    def ls_members(cls, c_id):
        pass

    @classmethod
    @abstractmethod
    def rm_member(cls, c_id, m_id):
        pass

    @classmethod
    def rm_members(cls, c_id, m_ids):
        return [cls.rm_member(c_id, m_id) for m_id in m_ids]

    @classmethod
    def member_exists(cls, c_id, qm_id):
        return qm_id in cls.ls_members(c_id)


class RAMStorageBackend(IStorageBackend):

    data = {}

    @classmethod
    def mint_container(cls):
        new_c_id = uuid4().hex
        cls.data[new_c_id] = set()
        return new_c_id

    @classmethod
    def rm_container(cls, c_id):
        del cls.data[c_id]
        return c_id

    @classmethod
    def ls_containers(cls):
        return list(cls.data.keys())

    @classmethod
    def add_member(cls, c_id, m_id):
        cls.data[c_id].add(m_id)
        return m_id

    @classmethod
    def rm_member(cls, c_id, m_id):
        cls.data[c_id].remove(m_id)
        return m_id

    @classmethod
    def ls_members(cls, c_id):
        return set(cls.data[c_id])


class MongoStorageBackend(IStorageBackend):

    # NOTE: This class assumes something else is assigning a .db attribute to it
    # so that it can communicate with the @classmethods. If you don't assign a
    # .db attribute to the class at some point, nothing will work. In this case,
    # we do this with some flask black magic callback nonsense on registering
    # the blueprint to an application at the bottom of this file.

    @classmethod
    def mint_container(cls):
        new_c = cls.db.containers.insert_one({'members': []})
        return str(new_c.inserted_id)

    @classmethod
    def rm_container(cls, c_id):
        r = cls.db.containers.delete_one({'_id': ObjectId(c_id)})
        if r.deleted_count < 1:
            raise KeyError
        return c_id

    @classmethod
    def ls_containers(cls):
        return [str(x['_id']) for x in cls.db.containers.find()]

    @classmethod
    def add_member(cls, c_id, m_id):
        r = cls.db.containers.update_one({'_id': ObjectId(c_id)}, {'$push': {'members': m_id}})
        if r.modified_count < 1:
            raise KeyError
        return m_id

    @classmethod
    def rm_member(cls, c_id, m_id):
        r = cls.db.containers.update_one({'_id': ObjectId(c_id)}, {'$pull': {'members': m_id}})
        if r.modified_count < 1:
            raise KeyError
        return m_id

    @classmethod
    def ls_members(cls, c_id):
        try:
            c = cls.db.containers.find_one({'_id': ObjectId(c_id)})
            if c is None:
                raise KeyError
        except InvalidId:
            raise KeyError
        return set(c['members'])


# Assigning the backend to use needs to be diferred until after the configs
# been potentially altered by the app context in order to set configuration
# values.
# Thus this function

def get_backend():
    if BLUEPRINT.config.get('STORAGE_BACKEND') == "MONGODB":
        return MongoStorageBackend
    else:
        return RAMStorageBackend


class Root(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('num', type=int,
                            help="How many containers to mint.",
                            default=1)
        args = parser.parse_args()
        return {
            "Minted": [{"identifier": x, "_link": API.url_for(Container, container_id=x)} for
                       x in get_backend().mint_containers(args['num'])],
            "_self": {"identifier": None, "_link": API.url_for(Root)}
        }

    def get(self):
        return {
            "Containers": [{"identifier": x, "_link": API.url_for(Container, container_id=x)} for
                           x in get_backend().ls_containers()],
            "_self": {"identifier": None, "_link": API.url_for(Root)}
        }


class Container(Resource):
    def post(self, container_id):
        parser = reqparse.RequestParser()
        parser.add_argument('member', type=str, help="The member id to add",
                            action="append", required=True)
        args = parser.parse_args()
        try:
            return {
                "Added": [{"identifier": x, "_link": API.url_for(Member, container_id=container_id, member_id=x)} for
                          x in get_backend().add_members(container_id, args['member'])],
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            abort(404)

    def get(self, container_id):
        try:
            return {
                "Members": [{"identifier": x, "_link": API.url_for(Member, container_id=container_id, member_id=x)} for
                            x in get_backend().ls_members(container_id)],
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            abort(404)

    def delete(self, container_id):
        try:
            get_backend().rm_container(container_id)
            return {
                "Deleted": True,
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            abort(404)


class Member(Resource):
    def get(self, container_id, member_id):
        try:
            if member_id in get_backend().ls_members(container_id):
                return {
                    "_self": {"identifier": member_id, "_link": API.url_for(Member, container_id=container_id, member_id=member_id)},
                    "Container": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
                }
            else:
                raise KeyError
        except KeyError:
            abort(404)

    def delete(self, container_id, member_id):
        try:
            get_backend().rm_member(container_id, member_id)
            return {
                "Deleted": True,
                "_self": {"identifier": member_id, "_link": API.url_for(Member, container_id=container_id, member_id=member_id)},
                "Container": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            abort(404)

# Let the application context clober any config options here
@BLUEPRINT.record
def handle_configs(setup_state):
    app = setup_state.app
    BLUEPRINT.config.update(app.config)
    if BLUEPRINT.config.get("STORAGE_BACKEND") == "MONGODB":
        client = MongoClient(BLUEPRINT.config.get("MONGO_HOST"),
                             BLUEPRINT.config.get("MONGO_PORT"))
        MongoStorageBackend.db = client[BLUEPRINT.config.get("MONGO_DB")]

API.add_resource(Root, "/")
# Trailing slash as a reminder that this is "directory-esque"
API.add_resource(Container, "/<string:container_id>/")
API.add_resource(Member, "/<string:container_id>/<string:member_id>")

from uuid import uuid4
from abc import ABCMeta, abstractmethod
import logging

from flask import Blueprint, abort, Response
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


log = logging.getLogger(__name__)


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


def output_html(data, code, headers=None):
    # https://github.com/flask-restful/flask-restful/issues/124
    resp = Response(data, mimetype='text/html', headers=headers)
    resp.status_code = code
    return resp


class Root(Resource):
    def post(self):
        log.info("Received POST @ root endpoint")
        log.debug("Parsing arguments")
        parser = reqparse.RequestParser()
        parser.add_argument('num', type=int,
                            help="How many containers to mint.",
                            default=1)
        args = parser.parse_args()
        log.debug("Arguments parsed")
        return {
            "Minted": [{"identifier": x, "_link": API.url_for(Container, container_id=x)} for
                       x in get_backend().mint_containers(args['num'])],
            "_self": {"identifier": None, "_link": API.url_for(Root)}
        }

    def get(self):
        log.info("Received GET @ root endpoint")
        return {
            "Containers": [{"identifier": x, "_link": API.url_for(Container, container_id=x)} for
                           x in get_backend().ls_containers()],
            "_self": {"identifier": None, "_link": API.url_for(Root)}
        }

class HTMLMint(Resource):
    def get(self):
        log.info("Received GET @ HTML mint endpoint")
        resp = """<html>
    <body>
        <h1>
		Mint a Container Identifier
        </h1>
        <form action=".."
        method="post">
        <p>
		<div>
        <input type="submit" value="Mint">
        </div>
        </form>
    </body>
</html>"""
        return output_html(resp, 200)


class HTMLMemberAdd(Resource):
    def get(self, container_id):
        log.info("Received GET @ HTML member add endpoint")
        resp = """<html>
    <body>
        <h1>
        Add a member to Container {}
        </h1>
        <form action="../{}/"
        method="post">
		<p>
        Member Identifier:<br>
        <input type="text" name="member" size="30">
        </p>
		<div>
        <input type="submit" value="Add">
        </div>
        </form>
    </body>
</html>""".format(container_id, container_id)
        return output_html(resp, 200)


class Container(Resource):
    def post(self, container_id):
        log.info("Received POST @ Container endpoint")
        log.debug("Parsing args")
        parser = reqparse.RequestParser()
        parser.add_argument('member', type=str, help="The member id to add",
                            action="append", required=True)
        args = parser.parse_args()
        log.debug("Args parsed")
        try:
            return {
                "Added": [{"identifier": x, "_link": API.url_for(Member, container_id=container_id, member_id=x)} for
                          x in get_backend().add_members(container_id, args['member'])],
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            log.critical("Container with id {} not found".format(container_id))
            abort(404)

    def get(self, container_id):
        log.info("Received GET @ Container endpoint")
        try:
            return {
                "Members": [{"identifier": x, "_link": API.url_for(Member, container_id=container_id, member_id=x)} for
                            x in get_backend().ls_members(container_id)],
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            log.critical("Container with id {} not found".format(container_id))
            abort(404)

    def delete(self, container_id):
        log.info("Received DELETE @ Container endpoint")
        try:
            get_backend().rm_container(container_id)
            return {
                "Deleted": True,
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            log.critical("Container with id {} not found".format(container_id))
            abort(404)


class Member(Resource):
    def get(self, container_id, member_id):
        log.info("Received GET @ Member endpoint")
        try:
            if member_id in get_backend().ls_members(container_id):
                return {
                    "_self": {"identifier": member_id, "_link": API.url_for(Member, container_id=container_id, member_id=member_id)},
                    "Container": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
                }
            else:
                raise KeyError
        except KeyError:
            log.critical("Container with id {} ".format(container_id) +
                        "or member with id {} ".format(member_id) +
                        "not found")
            abort(404)

    def delete(self, container_id, member_id):
        log.info("Received DELETE @ Member endpoint")
        try:
            get_backend().rm_member(container_id, member_id)
            return {
                "Deleted": True,
                "_self": {"identifier": member_id, "_link": API.url_for(Member, container_id=container_id, member_id=member_id)},
                "Container": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            log.critical("Container with id {} ".format(container_id) +
                        "or member with id {} ".format(member_id) +
                        "not found")
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
    if BLUEPRINT.config.get("VERBOSITY"):
        logging.basicConfig(level=BLUEPRINT.config['VERBOSITY'])
    else:
        logging.basicConfig(level="WARN")


API.add_resource(Root, "/")
API.add_resource(HTMLMint, "/mint")
API.add_resource(HTMLMemberAdd, "/<string:container_id>/add")
# Trailing slash as a reminder that this is "directory-esque"
API.add_resource(Container, "/<string:container_id>/")
API.add_resource(Member, "/<string:container_id>/<string:member_id>")

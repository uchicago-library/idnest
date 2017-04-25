from uuid import uuid4
from abc import ABCMeta, abstractmethod
import logging

from flask import Blueprint, abort, Response
from flask_restful import Resource, Api, reqparse
from pymongo import MongoClient, ASCENDING
import redis


BLUEPRINT = Blueprint('idnest', __name__)


BLUEPRINT.config = {
    'STORAGE_BACKEND': 'noerror'
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
    @abstractmethod
    def mint_container(self):
        pass

    def mint_containers(self, num):
        return [self.mint_container() for _ in range(num)]

    @abstractmethod
    def rm_container(self, c_id):
        pass

    def rm_containers(self, c_ids):
        return [self.rm_container(c_id) for c_id in c_ids]

    @abstractmethod
    def ls_containers(self, cursor, limit):
        pass

    @abstractmethod
    def container_exists(self, qc_id):
        pass

    @abstractmethod
    def add_member(self, c_id, m_id):
        pass

    def add_members(self, c_id, m_ids):
        return [self.add_member(c_id, m_id) for m_id in m_ids]

    @abstractmethod
    def ls_members(self, c_id, cursor, limit):
        pass

    @abstractmethod
    def rm_member(self, c_id, m_id):
        pass

    def rm_members(self, c_id, m_ids):
        return [self.rm_member(c_id, m_id) for m_id in m_ids]

    @abstractmethod
    def member_exists(self, c_id, qm_id):
        pass


class RAMStorageBackend(IStorageBackend):
    def __init__(self, bp):
        self.data = {}

    def mint_container(self):
        new_c_id = uuid4().hex
        self.data[new_c_id] = []
        return new_c_id

    def rm_container(self, c_id):
        try:
            del self.data[c_id]
        except KeyError:
            pass
        return c_id

    def ls_containers(self, cursor, limit):
        def peek(cursor, limit):
            try:
                sorted(self.data.keys())[cursor+limit]
                return str(cursor+limit)
            except IndexError:
                return None
        cursor = int(cursor)
        return peek(cursor, limit), list(sorted(self.data.keys()))[cursor:cursor+limit]

    def add_member(self, c_id, m_id):
        self.data[c_id].append(m_id)
        return m_id

    def rm_member(self, c_id, m_id):
        try:
            self.data[c_id].remove(m_id)
        except ValueError:
            pass
        return m_id

    def ls_members(self, c_id, cursor, limit):
        def peek(cursor, limit):
            try:
                self.data[c_id][cursor+limit]
                return str(cursor+limit)
            except IndexError:
                return None
        cursor = int(cursor)
        return peek(cursor, limit), self.data[c_id][cursor:cursor+limit]

    def container_exists(self, c_id):
        return c_id in self.data.keys()

    def member_exists(self, c_id, m_id):
        try:
            return m_id in self.data[c_id]
        except KeyError:
            return False


class MongoStorageBackend(IStorageBackend):
    def __init__(self, bp):
        client = MongoClient(bp.config["MONGO_HOST"],
                             bp.config.get("MONGO_PORT", 27017))
        self.db = client[bp.config["MONGO_DB"]]

    def mint_container(self):
        id = uuid4().hex
        self.db.containers.insert_one({'members': [], '_id': id})
        return id

    def rm_container(self, c_id):
        self.db.containers.delete_one({'_id': c_id})
        return c_id

    def ls_containers(self, cursor, limit):
        def peek(cursor, limit):
            if len([str(x['_id']) for x in
                    self.db.containers.find().sort('_id', ASCENDING).\
                    skip(cursor+limit).limit(1)]) > 0:
                    return str(cursor+limit)
            else:
                    return None
        cursor = int(cursor)
        return peek(cursor, limit), [str(x['_id']) for x in self.db.containers.find().sort('_id', ASCENDING).skip(cursor).limit(limit)]

    def add_member(self, c_id, m_id):
        r = self.db.containers.update_one({'_id': c_id}, {'$push': {'members': m_id}})
        if r.modified_count < 1:
            raise KeyError
        return m_id

    def rm_member(self, c_id, m_id):
        self.db.containers.update_one({'_id': c_id}, {'$pull': {'members': m_id}})
        return m_id

    def ls_members(self, c_id, cursor, limit):
        def peek(cursor, limit, members):
            try:
                members[cursor+limit]
                return str(cursor+limit)
            except IndexError:
                return None
        cursor = int(cursor)
        c = self.db.containers.find_one({'_id': c_id})
        return peek(cursor, limit, c['members']), c['members'][cursor:cursor+limit]

    def container_exists(self, c_id):
        return bool(self.db.containers.find_one({'_id': c_id}))

    def member_exists(self, c_id, m_id):
        c = self.db.containers.find_one({'_id': c_id})
        if c is None:
            return False
        return m_id in c['members']


class RedisStorageBackend(IStorageBackend):
    def __init__(self, bp):
        self.r = redis.StrictRedis(
            host=bp.config["REDIS_HOST"],
            port=bp.config.get("REDIS_PORT", 6379),
            db=bp.config["REDIS_DB"]
        )

    def mint_container(self):
        c_id = uuid4().hex
        self.r.lpush(c_id, 0)
        return c_id

    def rm_container(self, c_id):
        self.r.delete(c_id)
        return c_id

    def ls_containers(self, cursor, limit):
        results = []
        while cursor != 0 and limit != 0:
            cursor, data = self.r.scan(cursor=cursor, count=limit)
            if limit:
                limit = limit - len(data)
            for item in data:
                results.append(item)
        return None if cursor == 0 else str(cursor), [x.decode("utf-8") for x in results]

    def container_exists(self, c_id):
        return c_id in self.r

    def add_member(self, c_id, m_id):
        if not self.container_exists(c_id):
            raise KeyError(
                "Can't put a member in a container that doesn't exist. c_id: {}".format(
                    c_id
                )
            )
        self.r.rpush(c_id, m_id)
        return m_id

    def ls_members(self, c_id, cursor, limit):
        def peek(c_id, cursor, limit):
            if len([x for x in self.r.lrange(c_id, cursor+limit, 1)]) > 0:
                return str(cursor+limit)
            else:
                return None
        cursor = int(cursor)
        # Skip the 0 we're using to keep Redis from deleting our key
        cursor = cursor+1
        limit = cursor+limit
        return peek(c_id, cursor, limit), [x.decode("utf-8") for x in self.r.lrange(c_id, cursor, limit)]

    def rm_member(self, c_id, m_id):
        self.r.lrem(c_id, 1, m_id)
        return m_id

    def member_exists(self, c_id, m_id):
        return m_id in (x.decode("utf-8") for x in self.r.lrange(c_id, 1, -1))


def output_html(data, code, headers=None):
    # https://github.com/flask-restful/flask-restful/issues/124
    resp = Response(data, mimetype='text/html', headers=headers)
    resp.status_code = code
    return resp

pagination_args_parser = reqparse.RequestParser()
pagination_args_parser.add_argument(
    'cursor', type=str, default="0"
)
pagination_args_parser.add_argument(
    'limit', type=int, default=1000
)


def check_limit(limit):
    if limit > BLUEPRINT.config.get("MAX_LIMIT", 1000):
        log.warn(
            "Received request above MAX_LIMIT (or 1000 if undefined), capping.")
        limit = BLUEPRINT.config.get("MAX_LIMIT", 1000)
    return limit


class Root(Resource):
    def post(self):
        log.info("Received POST @ root endpoint")
        log.debug("Parsing arguments")
        parser = reqparse.RequestParser()
        parser.add_argument('num', type=int,
                            help="How many containers to mint.",
                            default=1)
        args = parser.parse_args()
        args['num'] = check_limit(args['num'])
        log.debug("Arguments parsed")
        return {
            "Minted": [{"identifier": x, "_link": API.url_for(Container, container_id=x)} for
                       x in BLUEPRINT.config['storage'].mint_containers(args['num'])],
            "_self": {"identifier": None, "_link": API.url_for(Root)}
        }

    def get(self):
        log.info("Received GET @ root endpoint")
        log.debug("Parsing args")
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        args['limit'] = check_limit(args['limit'])
        paginated_ids = BLUEPRINT.config['storage'].ls_containers(cursor=args['cursor'], limit=args['limit'])[1]
        return {
            "Containers": [{"identifier": x, "_link": API.url_for(Container, container_id=x)} for
                           x in paginated_ids],
            "cursor": args['cursor'],
            "limit": args['limit'],
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
        <form action="."
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
        <form action="./{}/"
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
                          x in BLUEPRINT.config['storage'].add_members(container_id, args['member'])],
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            log.critical("Container with id {} not found".format(container_id))
            abort(404)

    def get(self, container_id):
        log.info("Received GET @ Container endpoint")
        parser = pagination_args_parser.copy()
        args = parser.parse_args()
        args['limit'] = check_limit(args['limit'])
        try:
            if not BLUEPRINT.config['storage'].container_exists(container_id):
                raise KeyError
            paginated_ids = BLUEPRINT.config['storage'].ls_members(container_id, cursor=args['cursor'], limit=args['limit'])[1]
            return {
                "Members": [{"identifier": x, "_link": API.url_for(Member, container_id=container_id, member_id=x)} for
                            x in paginated_ids],
                "cursor": args['cursor'],
                "limit": args['limit'],
                "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
            }
        except KeyError:
            log.critical("Container with id {} not found".format(container_id))
            abort(404)

    def delete(self, container_id):
        log.info("Received DELETE @ Container endpoint")
        BLUEPRINT.config['storage'].rm_container(container_id)
        return {
            "Deleted": True,
            "_self": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
        }


class Member(Resource):
    def get(self, container_id, member_id):
        log.info("Received GET @ Member endpoint")
        try:
            if BLUEPRINT.config['storage'].member_exists(container_id, member_id):
                return {
                    "_self": {"identifier": member_id, "_link": API.url_for(Member, container_id=container_id, member_id=member_id)},
                    "Container": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
                }
            else:
                raise KeyError()
        except KeyError:
            log.critical("Container with id {} ".format(container_id) +
                         "or member with id {} ".format(member_id) +
                         "not found")
            abort(404)

    def delete(self, container_id, member_id):
        log.info("Received DELETE @ Member endpoint")
        BLUEPRINT.config['storage'].rm_member(container_id, member_id)
        return {
            "Deleted": True,
            "_self": {"identifier": member_id, "_link": API.url_for(Member, container_id=container_id, member_id=member_id)},
            "Container": {"identifier": container_id, "_link": API.url_for(Container, container_id=container_id)}
        }


# Let the application context clobber any config options here
@BLUEPRINT.record
def handle_configs(setup_state):
    app = setup_state.app
    BLUEPRINT.config.update(app.config)

    storage_choice = BLUEPRINT.config.get("STORAGE_BACKEND")
    if storage_choice is None:
        raise RuntimeError(
            "Missing required configuration value 'STORAGE_BACKEND'"
        )
    if not isinstance(storage_choice, str):
        raise TypeError(
            "STORAGE_BACKEND value is not a str, is instead a {}".format(
                str(type(storage_choice))
            )
        )

    supported_backends = {
        "mongodb": MongoStorageBackend,
        "redis": RedisStorageBackend,
        "ram": RAMStorageBackend,
        "noerror": None
    }

    if storage_choice.lower() not in supported_backends:
        raise RuntimeError(
            "Unsupported STORAGE_BACKEND: {}\n".format(storage_choice) +
            "Supported storage backends include: " +
            "{}".format(", ".join(supported_backends.keys()))
        )
    elif storage_choice.lower() == 'noerror':
        pass
    else:
        BLUEPRINT.config['storage'] = supported_backends.get(storage_choice.lower())(BLUEPRINT)

    if BLUEPRINT.config.get("VERBOSITY") is None:
        BLUEPRINT.config["VERBOSITY"] = "WARN"
    logging.basicConfig(level=BLUEPRINT.config["VERBOSITY"])


@BLUEPRINT.before_request
def before_request():
    # Check to be sure all our pre-request configuration has been done.
    if not isinstance(BLUEPRINT.config.get('storage'), IStorageBackend):
        raise RuntimeError("No storage backend is configured!")
        abort(500)


API.add_resource(Root, "/")
API.add_resource(HTMLMint, "/mint")
API.add_resource(HTMLMemberAdd, "/<string:container_id>/add")
# Trailing slash as a reminder that this is "directory-esque"
API.add_resource(Container, "/<string:container_id>/")
API.add_resource(Member, "/<string:container_id>/<string:member_id>")

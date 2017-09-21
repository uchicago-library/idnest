# idnest

v0.0.1

[![Build Status](https://travis-ci.org/uchicago-library/idnest.svg?branch=master)](https://travis-ci.org/uchicago-library/idnest) [![Coverage Status](https://coveralls.io/repos/github/uchicago-library/idnest/badge.svg?branch=master)](https://coveralls.io/github/uchicago-library/idnest?branch=master)

A RESTful API for nested identifier association

# Debug Quickstart
Set environmental variables appropriately
```
./debug.sh
```

# Docker Quickstart
Inject environmental variables appropriately at either buildtime or runtime
```
# docker build . -t idnest
# docker run -p 5000:80 idnest --name my_idnest
```

# Basic Usage

Nothing here to begin with
```
$ curl -s 127.0.0.1:5000 | python -m json.tool
{
    "Containers": [],
    "_self": {
        "_link": "/",
        "identifier": null
    }
}
```

Make container #1
```
$ curl -s 127.0.0.1:5000 -X POST | python -m json.tool
{
    "Minted": [
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/",
            "identifier": "6e02516a7ea1435a886f1cd406465e74"
        }
    ],
    "_self": {
        "_link": "/",
        "identifier": null
    }
}
```

Make container #2
```
$ curl -s 127.0.0.1:5000 -X POST | python -m json.tool
{
    "Minted": [
        {
            "_link": "/e0724e3ca9a645f2be83d780f0394ede/",
            "identifier": "e0724e3ca9a645f2be83d780f0394ede"
        }
    ],
    "_self": {
        "_link": "/",
        "identifier": null
    }
}
```

There's stuff here now
```
$ curl -s 127.0.0.1:5000 | python -m json.tool
{
    "Containers": [
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/",
            "identifier": "6e02516a7ea1435a886f1cd406465e74"
        },
        {
            "_link": "/e0724e3ca9a645f2be83d780f0394ede/",
            "identifier": "e0724e3ca9a645f2be83d780f0394ede"
        }
    ],
    "_self": {
        "_link": "/",
        "identifier": null
    }
}
```

Nothing in either of our containers
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/ | python -m json.tool
{
    "Members": [],
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    }
}

$ curl -s 127.0.0.1:5000/e0724e3ca9a645f2be83d780f0394ede/ | python -m json.tool
{
    "Members": [],
    "_self": {
        "_link": "/e0724e3ca9a645f2be83d780f0394ede/",
        "identifier": "e0724e3ca9a645f2be83d780f0394ede"
    }
}
```

Delete a container
```
$ curl -s 127.0.0.1:5000/e0724e3ca9a645f2be83d780f0394ede/ -X DELETE | python -m json.tool
{
    "Deleted": true,
    "_self": {
        "_link": "/e0724e3ca9a645f2be83d780f0394ede/",
        "identifier": "e0724e3ca9a645f2be83d780f0394ede"
    }
}
```

No more container, we get 404'd if we ask for it.
```
$ curl -s 127.0.0.1:5000/e0724e3ca9a645f2be83d780f0394ede/ | python -m json.tool
{
    "message": "The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again."
}
```

And its not in our container listing anymore
```
$ curl -s 127.0.0.1:5000 | python -m json.tool
{
    "Containers": [
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/",
            "identifier": "6e02516a7ea1435a886f1cd406465e74"
        }
    ],
    "_self": {
        "_link": "/",
        "identifier": null
    }
}
```

Add some members to our existing container...

One at a time
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/ -X POST -F "member"="123" | python -m json.tool
{
    "Added": [
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/123",
            "identifier": "123"
        }
    ],
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    }
}
```

Or in bulk
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/ -X POST -F "member"="456" -F "member"="789" | python -m json.tool
{
    "Added": [
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/456",
            "identifier": "456"
        },
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/789",
            "identifier": "789"
        }
    ],
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    }
}
```

View member listings
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/ | python -m json.tool
{
    "Members": [
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/789",
            "identifier": "789"
        },
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/456",
            "identifier": "456"
        },
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/123",
            "identifier": "123"
        }
    ],
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    }
}
```

View a member of a container
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/123 | python -m json.tool
{
    "Container": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    },
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/123",
        "identifier": "123"
    }
}
```

No member == 404
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/321 | python -m json.tool
{
    "message": "The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again."
}

```

Delete a member
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/123 -X DELETE | python -m json.tool
{
    "Container": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    },
    "Deleted": true,
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/123",
        "identifier": "123"
    }
}
```

Member is no longer in the container...
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/ | python -m json.tool
{
    "Members": [
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/456",
            "identifier": "456"
        },
        {
            "_link": "/6e02516a7ea1435a886f1cd406465e74/789",
            "identifier": "789"
        }
    ],
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    }
}
```

Delete our container and its members...
```
$ curl -s 127.0.0.1:5000/6e02516a7ea1435a886f1cd406465e74/ -X DELETE | python -m json.tool
{
    "Deleted": true,
    "_self": {
        "_link": "/6e02516a7ea1435a886f1cd406465e74/",
        "identifier": "6e02516a7ea1435a886f1cd406465e74"
    }
}
```

```
$ curl -s 127.0.0.1:5000 | python -m json.tool
{
    "Containers": [],
    "_self": {
        "_link": "/",
        "identifier": null
    }
}
```

# Environmental Variables
## Required
- IDNEST_STORAGE_CHOICE: The backend to use to store the data
    - can be any of: redis, mongo, ram
### Required Per IDNEST_STORAGE_CHOICE
- redis
    - IDNEST_REDIS_HOST: The host address of the redis server
    - IDNEST_REDIS_DB: Which redis db to use on the server
- mongo
    - IDNEST_MONGO_HOST: The host address of the mongo server
    - IDNEST_MONGO_DB: The name of the mongo db to use on the server
-ram
    - None

## Optional
- IDNEST_DEFER_CONFIG: If set _no_ automatic configuration will occur
- IDNEST_VERBOSITY (warn): Verbosity to run logging at
### Optional per IDNEST_STORAGE_CHOICE
- redis
    - IDNEST_REDIS_PORT (6379): The port the server is running on
- mongo
    - IDNEST_MONGO_PORT (27017): The port the server is running on
-ram
    - None

# Author
Brian Balsamo <balsamo@uchicago.edu>

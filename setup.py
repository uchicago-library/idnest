from setuptools import setup, find_packages

def readme():
    with open("README.md", 'r') as f:
        return f.read()

setup(
    name = "idnest",
    version = "0.0.1",
    description = "A REST API for keeping track of nested relations of ids",
    long_description = readme(),
    packages = find_packages(
        exclude = [
        ]
    ),
    install_requires = [
        'flask>0',
        'flask_env',
        'flask_restful',
        'pymongo',
        'redis'
    ],
)

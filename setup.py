from setuptools import setup, find_packages


def readme():
    with open("README.md", 'r') as f:
        return f.read()


setup(
    name="idnest",
    description="A RESTful API for nested identifier association",
    version="0.0.1",
    long_description=readme(),
    author="Brian Balsamo",
    author_email="balsamo@uchicago.edu",
    packages=find_packages(
        exclude=[
        ]
    ),
    include_package_data=True,
    url='https://github.com/uchicago-library/idnest',
    install_requires=[
        'flask>0',
        'flask_env',
        'flask_restful',
        'pymongo',
        'redis'
    ],
    tests_require=[
        'pytest'
    ],
    test_suite='tests'
)

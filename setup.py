"""Setup module for Robot Framework TestRail Library package."""

# To use a consistent encoding
from codecs import open
from os import path

from setuptools import setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get install requires from requirements.txt
with open(path.join(here, 'requirements.txt')) as f:
    requirements = f.read().splitlines()

setup(
    name='robotframework-testrail',
    version='1.0.0',
    description='Robot Framework library, listener and pre-run modifier for working with TestRail',
    long_description=long_description,
    url='https://github.com/peterservice-rnd/robotframework-testrail',
    author='JSC PETER-SERVICE',
    author_email='drse_aist_all@billing.ru',
    license='Apache License 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Robot Framework :: Library',
    ],
    keywords='testing testautomation robotframework testrail',
    package_dir={'': 'src'},
    install_requires=requirements,
)

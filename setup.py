import os
from setuptools import setup, find_packages
from codecs import open

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='os-package-registry',
    version='0.0.2',
    description=(
        'Manage a registry of packages on an ElasticSearch instance'
    ),
    long_description=long_description,

    url='https://github.com/openspending/os-pacakge-registry',

    author='Open Knowledge International',
    author_email='info@okfn.org',

    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Topic :: Utilities',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='fdp fiscal data package openspending elasticsearch',

    packages=find_packages(exclude=['tests']),

    install_requires=[
        'elasticsearch',],
)

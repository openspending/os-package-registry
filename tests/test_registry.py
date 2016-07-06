 # -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from elasticsearch import Elasticsearch, NotFoundError

import os
import json
import pytest
import os_package_registry


MODEL_NAME, SAMPLE_DATA = json.load(open(os.path.join(os.path.dirname(__file__), 'sample.json')))

@pytest.fixture
def package_registry():
    LOCAL_ELASTICSEARCH = 'localhost:9200'
    es = Elasticsearch(hosts=[LOCAL_ELASTICSEARCH])
    try:
        es.indices.delete(index='packages')
    except NotFoundError:
        pass
    es.index(index='packages', doc_type='package', body=SAMPLE_DATA, id=MODEL_NAME)
    es.indices.flush('packages')
    return os_package_registry.PackageRegistry(es_connection_string=LOCAL_ELASTICSEARCH)


class TestPackageRegistry(object):

    def test_ok(self, package_registry):
        print("OK")

    def test_list_cubes_correct_values(self, package_registry):
        """
        Simple loading of one valid fdp into DB and testing correct CM values
        """
        models = list(package_registry.list_models())
        assert(len(models) == 1, 'no dataset was loaded')
        assert(models[0] == MODEL_NAME, 'dataset with wrong name')

    def test_get_cube_model_correct_values(self, package_registry):
        model = package_registry.get_model(MODEL_NAME)
        expected = MODEL_NAME.replace('-', '_').replace(':', '__').replace('@', '_').replace('.', '_')
        assert(model['fact_table'] == 'fdp__'+expected, 'bad model')

    def test_has_cube_correct_values(self, package_registry):
        assert(package_registry.has_model(MODEL_NAME))
        assert(not package_registry.has_model(MODEL_NAME+'1'))

    def test_no_such_cube(self, package_registry):
        with pytest.raises(KeyError):
            package_registry.get_model('bla')

    def test_get_package_correct_values(self, package_registry):
        package = package_registry.get_package(MODEL_NAME)
        assert(package['owner']+':'+package['name'] == MODEL_NAME, 'wrong model name')

    def test_no_such_package(self, package_registry):
        with pytest.raises(KeyError):
            package_registry.get_package('bla')
        with pytest.raises(KeyError):
            package_registry.get_raw('bla')

    def test_get_raw(self, package_registry):
        name, datapackage_url, datapackage, model, dataset_name, author = \
            package_registry.get_raw(MODEL_NAME)
        assert(name == MODEL_NAME)
        assert(datapackage_url == SAMPLE_DATA['origin_url'])
        assert(datapackage == SAMPLE_DATA['package'])
        assert(model == SAMPLE_DATA['model'])
        assert(dataset_name == SAMPLE_DATA['dataset'])
        assert(author == SAMPLE_DATA['author'])
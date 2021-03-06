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
from os_package_registry import PackageRegistry


MODEL_NAME, SAMPLE_DATA = json.load(open(os.path.join(os.path.dirname(__file__), 'sample.json')))

@pytest.fixture
def package_registry():
    LOCAL_ELASTICSEARCH = 'localhost:9200'
    es = Elasticsearch(hosts=[LOCAL_ELASTICSEARCH])
    try:
        es.indices.delete(index='papapa')
    except NotFoundError:
        pass
    pr = os_package_registry.PackageRegistry(es_connection_string=LOCAL_ELASTICSEARCH, index_name='papapa')
    es.index(index='papapa', doc_type='package', body=SAMPLE_DATA, id=MODEL_NAME)
    es.indices.flush('papapa')
    return pr


class TestPackageRegistry(object):

    def test_ok(self, package_registry):
        print("OK")

    def test_list_cubes_correct_values(self, package_registry):
        models = list(package_registry.list_models())
        assert len(models) == 1, 'no dataset was loaded'
        assert models[0] == MODEL_NAME, 'dataset with wrong name'

    def test_stats_correct_values(self, package_registry):
        stats = package_registry.get_stats()
        assert stats == {'num_countries': 1, 'num_packages': 1, 'num_records': 1234567}

    def test_delete(self, package_registry):
        models = list(package_registry.list_models())
        assert len(models) == 1, 'no dataset was loaded'
        assert models[0] == MODEL_NAME, 'dataset with wrong name'
        ret = package_registry.delete_model(MODEL_NAME)
        models = list(package_registry.list_models())
        assert len(models) == 0, 'dataset was not deleted'
        assert ret == True

    def test_get_cube_model_correct_values(self, package_registry):
        model = package_registry.get_model(MODEL_NAME)
        expected = MODEL_NAME.replace('-', '_').replace(':', '__').replace('@', '_').replace('.', '_')
        assert model['fact_table'] == 'fdp__'+expected, 'bad model'

    def test_has_cube_correct_values(self, package_registry):
        assert package_registry.has_model(MODEL_NAME)
        assert not package_registry.has_model(MODEL_NAME+'1')

    def test_no_such_cube(self, package_registry):
        with pytest.raises(KeyError):
            package_registry.get_model('bla')

    def test_get_package_correct_values(self, package_registry):
        package = package_registry.get_package(MODEL_NAME)
        assert package['owner']+':'+package['name'] == MODEL_NAME, 'wrong model name'

    def test_no_such_package(self, package_registry):
        with pytest.raises(KeyError):
            package_registry.get_package('bla')
        with pytest.raises(KeyError):
            package_registry.get_raw('bla')

    def test_get_raw(self, package_registry):
        name, datapackage_url, datapackage, model, dataset_name, author, status, loaded = \
            package_registry.get_raw(MODEL_NAME)
        assert name == MODEL_NAME
        assert datapackage_url == SAMPLE_DATA['origin_url']
        assert datapackage == SAMPLE_DATA['package']
        assert model == SAMPLE_DATA['model']
        assert dataset_name == SAMPLE_DATA['dataset']
        assert author == SAMPLE_DATA['author']
        assert status == SAMPLE_DATA['loading_status']
        assert loaded == SAMPLE_DATA['loaded']

    def test_save_and_update(self, package_registry: PackageRegistry):
        name = 'owner:my-name'
        dp_url = 'http://dp_url'
        dp = {'name': 'moses'}
        model = {'my-model': 'is-great'}
        dataset_name = 'ds-name'
        author = 'authors-name'
        status = 'FUNKY'
        loaded = False

        def check():
            name_, dp_url_, dp_, model_, dataset_name_, author_, status_, loaded_ = \
                package_registry.get_raw(name)
            assert name_ == name
            assert dp_url_ == dp_url
            assert dp_ == dp
            assert model_ == model
            assert dataset_name_ == dataset_name
            assert author_ == author
            assert status_ == status
            assert loaded_ == loaded

        package_registry.save_model(name, dp_url, dp, model, dataset_name, author, status, loaded)
        check()

        author = 'moses'
        package_registry.update_model(name, author=author)
        check()

        status = 'BLINKY'
        package_registry.update_model(name, status=status)
        check()

        status = 'AWESOME'
        loaded = True
        package_registry.update_model(name, status=status, loaded=loaded)
        check()

        # Update existing property of model
        model = {'my-model': 'replace model'}
        dp = {'name': 'replace name'}
        package_registry.update_model(name, model=model, datapackage=dp)
        check()

        # Replace model
        model = {'completely': 'replace model'}
        dp = {'completely': 'replace dp'}
        package_registry.update_model(name, model=model, datapackage=dp)
        check()

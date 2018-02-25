import logging
import time
from collections import namedtuple

from elasticsearch import Elasticsearch, NotFoundError


class PackageRegistry(object):

    PACKAGE_FIELDS = ['id', 'model', 'package', 'origin_url', 'author', 'dataset', 'loading_status', 'loaded']
    BATCH_SIZE = 100
    TABLE_NAME_PREFIX = "fdp__"
    Model = namedtuple('Model', PACKAGE_FIELDS)

    INDEX_NAME = 'packages'
    DOC_TYPE = 'package'

    MAPPING = {
        'id': {
            "type": "string",
            "index": "not_analyzed",
        },
        'model': {
            "type": "object",
            "index": "no",
            "enabled": False
        },
        'package': {
            'type': 'object',
            'properties': {
                'author': {
                    "type": "string",
                    "index": "not_analyzed",
                },
                'owner': {
                    "type": "string",
                    "index": "not_analyzed",
                },
                'cityCode': {
                    "type": "string",
                    "index": "not_analyzed",
                },
                'resources': {
                    "type": "object",
                    "properties": {
                        "schema": {
                            "type": "object",
                            "enabled": False
                        }
                    }
                },
                'model': {
                    "type": "object",
                    "index": "no",
                    "enabled": False
                },
            }
        },
        'origin_url': {
            "type": "string",
            "index": "not_analyzed",
        },
        'dataset': {
            "type": "string",
            "index": "not_analyzed",
        }
    }

    def __init__(self, es_connection_string=None, es_instance=None, index_name=INDEX_NAME):
        if es_instance is None:
            logging.info('Attempting to connect to ES: {0}'.format(es_connection_string))
            self.es = Elasticsearch(hosts=[es_connection_string])
            logging.info('Successful connection to ES')
            logging.info('Index name: %s', index_name)
        else:
            self.es = es_instance

        self.index_name = index_name
        if not self.es.indices.exists(self.index_name):
            self.es.indices.create(self.index_name)
        mapping = {self.DOC_TYPE: {'properties': self.MAPPING}}
        self.es.indices.put_mapping(doc_type=self.DOC_TYPE,
                                    index=self.index_name,
                                    body=mapping)


    def save_model(self, name, datapackage_url, datapackage,
                   model, dataset_name, author, status, loaded):
        """
        Save a model in the registry
        :param name: name for the model
        :param datapackage_url: origin URL for the datapackage which is the source for this model
        :param datapackage: datapackage object from which this model was derived
        :param dataset_name: Title of the dataset
        :param author: Author of the dataset
        :param model: model to save
        :param status: What's the status for loading
        :param loaded: Was the package loaded successfully
        """
        document = {
            # Fields used by babbage API
            'id': name,
            'model': model,
            'package': datapackage,
            'origin_url': datapackage_url,

            # Extra fields available in search
            'dataset': dataset_name,
            'author': author,
            'loading_status': status,
            'loaded': loaded,
            'last_update': time.time()
        }
        self.es.index(index=self.index_name, doc_type=self.DOC_TYPE, body=document, id=name)
        # Make sure that the data is saved
        self.es.indices.flush(self.index_name)


    def update_model(self, name, **kw):
        """
        Update a model in the registry (create if needed)
        :param name: name for the model
        :param datapackage_url: origin URL for the datapackage which is the source for this model
        :param datapackage: datapackage object from which this model was derived
        :param dataset_name: Title of the dataset
        :param author: Author of the dataset
        :param model: model to save
        :param status: What's the status for loading
        :param loaded: Was the package loaded successfully
        """

        document = {
            'id': name,
            'last_update': time.time()
        }
        for key, param in [
                ('model', 'model'),
                ('package', 'datapackage'),
                ('origin_url', 'datapackage_url'),
                ('dataset', 'dataset_name'),
                ('author', 'author'),
                ('loading_status', 'status'),
                ('loaded', 'loaded')
            ]:
            if param in kw:
                document[key] = kw[param]

        body = dict(
            doc=document,
            doc_as_upsert=True
        )
        self.es.update(index=self.index_name, doc_type=self.DOC_TYPE, body=body, id=name)
        # Make sure that the data is saved
        self.es.indices.flush(self.index_name)


    def delete_model(self, name):
        """
        Delete a model from the registry
        :param name: name for the model
        """
        try:
            ret = self.es.delete(index=self.index_name, doc_type=self.DOC_TYPE, id=name)
        except NotFoundError:
            return False
        # Make sure that the data is saved
        self.es.indices.flush(self.index_name)
        return ret['found']

    def get_raw(self, name):
        """
        Get all data for a package in the registry
        :returns tuple of:
            name: name for the model
            datapackage_url: origin URL for the datapackage which is the source for this model
            datapackage: datapackage object from which this model was derived
            dataset_name: Title of the dataset
            author: Author of the dataset
            model: model to save
        """
        try:
            ret = self.es.get(index=self.index_name, doc_type=self.DOC_TYPE, id=name, _source=self.PACKAGE_FIELDS)
            if ret['found']:
                source = ret['_source']
                return (name,
                        source.get('origin_url'),
                        source.get('package'),
                        source.get('model'),
                        source.get('dataset'),
                        source.get('author'),
                        source.get('loading_status'),
                        source.get('loaded', True))
            raise KeyError(name)
        except NotFoundError:
            raise KeyError(name)

    def list_models(self):
        """
        List all available models in the DB
        :return: A generator yielding strings (one per model)
        """
        try:
            count = self.es.count(index=self.index_name, doc_type=self.DOC_TYPE, q='*')['count']
            from_ = 0
            while from_ < count:
                ret = self.es.search(index=self.index_name, doc_type=self.DOC_TYPE, q='*',
                                     size=self.BATCH_SIZE, from_=from_, _source=self.PACKAGE_FIELDS)
                for hit in ret.get('hits',{}).get('hits', []):
                    yield hit['_source']['id']
                from_ += self.BATCH_SIZE
        except NotFoundError:
            return

    def get_stats(self):
        """
        Get some stats on the packages in the registry
        """
        try:
            query = {
                'size': 0,  # We only care about the aggregations, so don't return the hits
                'aggs': {
                    'num_packages': {
                        'value_count': {
                            'field': 'id',
                        },
                    },
                    'num_records': {
                        'sum': {
                            'field': 'count_of_rows',
                        },
                    },
                    'num_countries': {
                        'cardinality': {
                            'field': 'countryCode',
                        },
                    },
                },
            }
            aggregations = self.es.search(index=self.index_name, body=query)['aggregations']

            return {
                key: int(value['value'])
                for key, value in aggregations.items()
            }
        except NotFoundError:
            return {}

    def has_model(self, name):
        """
        Check if a model exists in the registry
        :param name: model name to test
        :return: True if yes
        """
        return self.es.exists(index=self.index_name, doc_type=self.DOC_TYPE, id=name)

    def get_model(self, name):
        """
        Return the model associated with a specific name.
        Raises KeyError in case the model doesn't exist.
        :param name: model name to fetch
        :return: Python object representing the model
        """
        try:
            ret = self.es.get(index=self.index_name, doc_type=self.DOC_TYPE, id=name, _source=self.PACKAGE_FIELDS)
            if ret['found']:
                return ret['_source']['model']
            raise KeyError(name)
        except NotFoundError:
            raise KeyError(name)

    def get_package(self, name):
        """
        Return the original package contents associated with a specific name.
        Raises KeyError in case the model doesn't exist.
        :param name: model name to fetch
        :return: Python object representing the package
        """
        try:
            rec = self.es.get(index=self.index_name, doc_type=self.DOC_TYPE, id=name, _source=self.PACKAGE_FIELDS)
            if rec['found']:
                ret = rec['_source']['package']
                ret['__origin_url'] = rec['_source']['origin_url']
                return ret
            raise KeyError(name)
        except NotFoundError:
            raise KeyError(name)

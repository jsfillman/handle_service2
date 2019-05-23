
import logging
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import subprocess
import traceback


class MongoUtil:

    HID_COUNTER_ID = 'hid_counter'

    def _start_service(self):
        logging.info('starting mongod service')

        logging.info('running sudo service mongodb start')
        pipe = subprocess.Popen("sudo service mongodb start", shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = pipe.communicate()
        logging.info(stdout)

        logging.info('running mongod --version')
        pipe = subprocess.Popen("mongod --version", shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = pipe.communicate()

        logging.info(stdout)

    def _get_collection(self, mongo_host, mongo_port, mongo_database, mongo_collection):
        """
        connect Mongo server and return a collection
        """

        my_client = MongoClient(mongo_host, mongo_port)

        try:
            my_client.server_info()  # force a call to server
        except ServerSelectionTimeoutError as e:
            error_msg = 'Connot connect to Mongo server\n'
            error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
            raise ValueError(error_msg)

        # TODO: check potential problems. MongoDB will create the collection if it does not exist.
        my_database = my_client[mongo_database]
        my_collection = my_database[mongo_collection]

        return my_collection

    def _inc_counter(self):
        counter = self.get_hid_counter()

        counter += 1

        update_filter = {'_id': self.HID_COUNTER_ID}
        update = {'$set': {self.HID_COUNTER_ID: counter}}
        self.hid_counter_collection.update_one(update_filter, update)

    def __init__(self, config):
        self.mongo_host = config['mongo-host']
        self.mongo_port = int(config['mongo-port'])
        self.mongo_database = config['mongo-database']
        self.mongo_collection = config['mongo-collection']
        self.mongo_hid_counter_collection = config['mongo-hid-counter-collection']

        self._start_service()
        self.handle_collection = self._get_collection(self.mongo_host, self.mongo_port,
                                                      self.mongo_database, self.mongo_collection)

        self.hid_counter_collection = self._get_collection(self.mongo_host, self.mongo_port,
                                                           self.mongo_database,
                                                           self.mongo_hid_counter_collection)

        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)

    def get_hid_counter(self):
        """
        get current handle id counter
        """
        counter = self.hid_counter_collection.find({'_id': {'$eq': self.HID_COUNTER_ID}})

        if counter.count():
            return counter.next().get('hid_counter')
        else:
            return 0

    def find_in(self, elements, field_name, projection={'_id': False}, batch_size=1000):
        """
        return cursor that contains docs which field column is in elements
        """
        logging.info('start querying MongoDB')

        try:
            result = self.handle_collection.find({field_name: {'$in': elements}},
                                                 projection=projection, batch_size=batch_size)
        except Exception as e:
            error_msg = 'Connot query doc\n'
            error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
            raise ValueError(error_msg)

        logging.info('returned {} results'.format(result.count()))

        return result

    def insert_one(self, doc):
        """
        insert a doc into collection
        """
        logging.info('start inserting document')

        try:
            self.handle_collection.insert_one(doc)
            self._inc_counter()
        except Exception as e:
            error_msg = 'Connot insert doc\n'
            error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
            raise ValueError(error_msg)

        return True

    def update_one(self, doc):
        """
        update a doc
        """
        logging.info('start updating document')

        try:
            update_filter = {'hid': doc.get('hid')}
            update = {'$set': doc}
            self.handle_collection.update_one(update_filter, update)
        except Exception as e:
            error_msg = 'Connot update doc\n'
            error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
            raise ValueError(error_msg)

        return True

    def delete_one(self, doc):
        """
        delete a doc
        """
        logging.info('start deleting document')

        try:
            delete_filter = {'hid': doc.get('hid')}
            self.handle_collection.delete_one(delete_filter)
        except Exception as e:
            error_msg = 'Connot delete doc\n'
            error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
            raise ValueError(error_msg)

        return True

    def delete_many(self, docs):
        """
        delete a docs
        """
        logging.info('start deleting documents')

        try:
            hids_to_delete = list(set([doc.get('hid') for doc in docs]))
            delete_filter = {'hid': {'$in': hids_to_delete}}
            result = self.handle_collection.delete_many(delete_filter)
        except Exception as e:
            error_msg = 'Connot delete docs\n'
            error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
            raise ValueError(error_msg)
        else:
            deleted_count = result.deleted_count

        return deleted_count

# -*- coding: utf-8 -*-
import os
import unittest
from configparser import ConfigParser
import inspect
import copy
import requests as _requests
from unittest.mock import patch

from AbstractHandle.authclient import KBaseAuth as _KBaseAuth
from mongo_util import MongoHelper
from AbstractHandle.Utils.Handler import Handler
from AbstractHandle.Utils.MongoUtil import MongoUtil


class HandlerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('AbstractHandle'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.cfg['admin-token'] = cls.token
        cls.cfg['mongo-collection'] = 'handle'
        cls.cfg['mongo-hid-counter-collection'] = 'handle_id_counter'

        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        cls.user_id = auth_client.get_user(cls.token)
        cls.shock_url = cls.cfg['shock-url']

        cls.mongo_helper = MongoHelper()
        cls.my_client = cls.mongo_helper.create_test_db(db=cls.cfg['mongo-database'],
                                                        col=cls.cfg['mongo-collection'])
        cls.handler = Handler(cls.cfg)
        cls.mongo_util = MongoUtil(cls.cfg)

        cls.shock_ids_to_delete = list()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'shock_ids_to_delete'):
            print('Nodes to delete: {}'.format(cls.shock_ids_to_delete))
            cls.deleteShockID(cls.shock_ids_to_delete)
        print('Finished testing Handler')

    @classmethod
    def deleteShockID(cls, shock_ids):
        headers = {'Authorization': 'OAuth {}'.format(cls.token)}
        for shock_id in shock_ids:
            end_point = os.path.join(cls.shock_url, 'node', shock_id)
            resp = _requests.delete(end_point, headers=headers, allow_redirects=True)
            if resp.status_code != 200:
                print('Cannot detele shock node ' + shock_id)
            else:
                print('Deleted shock node ' + shock_id)

    def getHandler(self):
        return self.__class__.handler

    def start_test(self):
        testname = inspect.stack()[1][3]
        print('\n*** starting test: ' + testname + ' **')

    def createTestNode(self):
        headers = {'Authorization': 'OAuth {}'.format(self.token)}

        end_point = os.path.join(self.shock_url, 'node')

        resp = _requests.post(end_point, headers=headers)

        if resp.status_code != 200:
            raise ValueError('Grant user readable access failed.\nError Code: {}\n{}\n'
                             .format(resp.status_code, resp.text))
        else:
            shock_id = resp.json().get('data').get('id')
            self.shock_ids_to_delete.append(shock_id)
            return shock_id

    def test_init_ok(self):
        self.start_test()
        class_attri = ['mongo_util', 'shock_util', 'token_cache', 'auth_url', 'admin_roles']
        handler = self.getHandler()
        self.assertTrue(set(class_attri) <= set(handler.__dict__.keys()))

    def test_fetch_handles_by_fail(self):
        self.start_test()
        handler = self.getHandler()

        with self.assertRaises(ValueError) as context:
            handler.fetch_handles_by({'missing_element': 'element', 'field_name': 'field_name'})

        self.assertIn('Required keys', str(context.exception.args))

        with self.assertRaises(ValueError) as context:
            handler.fetch_handles_by({'element': 'element', 'missing_field_name': 'field_name'})

        self.assertIn('Required keys', str(context.exception.args))

    def test_fetch_handles_by_okay(self):
        self.start_test()
        handler = self.getHandler()

        # test query 'hid' field
        elements = ['KBH_68020', 'KBH_68022', 'fake_id']
        field_name = 'hid'
        handles = handler.fetch_handles_by({'elements': elements, 'field_name': field_name})
        self.assertEqual(len(handles), 2)
        self.assertCountEqual(elements[:2], [h.get('hid') for h in handles])

        # test query 'hid' field with empty data
        elements = [0]
        field_name = 'hid'
        handles = handler.fetch_handles_by({'elements': elements, 'field_name': field_name})
        self.assertEqual(len(handles), 0)

        # test query 'id' field
        elements = ['b753774f-0bbd-4b96-9202-89b0c70bf31c']
        field_name = 'id'
        handles = handler.fetch_handles_by({'elements': elements, 'field_name': field_name})
        self.assertEqual(len(handles), 1)
        handle = handles[0]
        self.assertFalse('_id' in handle)
        self.assertEqual(handle.get('hid'), 'KBH_68020')

    def test_persist_handle_fail(self):
        self.start_test()
        handler = self.getHandler()

        with self.assertRaises(ValueError) as context:
            handle = {'missing_id': 'id'}
            handler.persist_handle(handle, self.user_id)

        self.assertIn('Missing one or more required positional field', str(context.exception.args))

        with self.assertRaises(ValueError) as context:
            handle = {'id': ''}
            handler.persist_handle(handle, self.user_id)

        self.assertIn('Missing one or more required positional field', str(context.exception.args))

        with self.assertRaises(ValueError) as context:
            handle = {'file_name': None}
            handler.persist_handle(handle, self.user_id)

        self.assertIn('Missing one or more required positional field', str(context.exception.args))

    def test_persist_handle_okay(self):
        self.start_test()
        handler = self.getHandler()

        handle = {'id': 'id',
                  'file_name': 'file_name',
                  'type': 'shock',
                  'url': 'http://ci.kbase.us:7044/'}
        # testing persist_handle with non-existing handle (inserting a handle)
        counter = handler.mongo_util.get_hid_counter()
        hid = handler.persist_handle(handle, self.user_id)
        new_counter = handler.mongo_util.get_hid_counter()
        self.assertEqual(new_counter, counter + 1)  # counter should increment
        handles = handler.fetch_handles_by({'elements': [hid], 'field_name': 'hid'})
        self.assertEqual(len(handles), 1)
        handle = handles[0]
        self.assertEqual(hid, 'KBH_' + str(counter))
        self.assertEqual(handle.get('hid'), hid)
        self.assertEqual(handle.get('id'), 'id')
        self.assertEqual(handle.get('file_name'), 'file_name')
        self.assertEqual(handle.get('created_by'), self.user_id)

        # testing persist_handle with existing handle (updating a handle)
        new_handle = copy.deepcopy(handle)
        new_file_name = 'new_file_name'
        new_id = 'new_id'
        new_handle['file_name'] = new_file_name
        new_handle['id'] = new_id
        counter = handler.mongo_util.get_hid_counter()
        new_hid = handler.persist_handle(new_handle, self.user_id)
        new_counter = handler.mongo_util.get_hid_counter()
        self.assertEqual(new_counter, counter)  # counter shouldn't increment
        handles = handler.fetch_handles_by({'elements': [new_hid], 'field_name': 'hid'})
        self.assertEqual(len(handles), 1)
        handle = handles[0]
        self.assertEqual(new_hid, 'KBH_' + str(counter-1))
        self.assertEqual(handle.get('hid'), hid)
        self.assertEqual(handle.get('id'), new_id)
        self.assertEqual(handle.get('file_name'), new_file_name)
        self.assertEqual(handle.get('created_by'), self.user_id)

        self.assertEqual(new_hid, hid)

        self.mongo_util.delete_one(handle)

    def test_delete_handles_fail(self):
        self.start_test()
        handler = self.getHandler()

        with self.assertRaises(ValueError) as context:
            handles = [{'created_by': 'fake_user'}]
            handler.delete_handles(handles, self.user_id)

        self.assertIn('Cannot delete handles not created by owner', str(context.exception.args))

    def test_delete_handles_ok(self):
        self.start_test()
        handler = self.getHandler()

        handles = [{'id': 'id',
                    'file_name': 'file_name',
                    'type': 'shock',
                    'url': 'http://ci.kbase.us:7044/'}] * 2
        hids_to_delete = list()
        for handle in handles:
            hid = handler.persist_handle(handle, self.user_id)
            hids_to_delete.append(hid)

        handles_to_delete = handler.fetch_handles_by({'elements': hids_to_delete, 'field_name': 'hid'})

        delete_count = handler.delete_handles(handles_to_delete, self.user_id)

        self.assertEqual(delete_count, len(hids_to_delete))

    def test_is_owner_ok(self):
        self.start_test()
        handler = self.getHandler()
        node_id = self.createTestNode()

        hids = list()

        handle = {'id': node_id,
                  'file_name': 'file_name',
                  'type': 'shock',
                  'url': self.shock_url}
        hid = handler.persist_handle(handle, self.user_id)
        hids.append(hid)

        is_owner = handler.is_owner(hids, self.token, self.user_id)
        self.assertTrue(is_owner)

        is_owner = handler.is_owner(hids, self.token, 'fake_user_100')
        self.assertFalse(is_owner)

        handles_to_delete = handler.fetch_handles_by({'elements': hids, 'field_name': 'hid'})
        delete_count = handler.delete_handles(handles_to_delete, self.user_id)
        self.assertEqual(delete_count, len(hids))

    def test_are_readable_ok(self):
        self.start_test()
        handler = self.getHandler()
        node_id_1 = self.createTestNode()
        node_id_2 = self.createTestNode()

        hids = list()

        handle = {'id': node_id_1,
                  'file_name': 'file_name',
                  'type': 'shock',
                  'url': self.shock_url}
        hid = handler.persist_handle(handle, self.user_id)
        hids.append(hid)

        handle = {'id': node_id_2,
                  'file_name': 'file_name',
                  'type': 'shock',
                  'url': self.shock_url}
        hid = handler.persist_handle(handle, self.user_id)
        hids.append(hid)

        are_readable = handler.are_readable(hids, self.token)
        self.assertTrue(are_readable)

        handles_to_delete = handler.fetch_handles_by({'elements': hids, 'field_name': 'hid'})
        delete_count = handler.delete_handles(handles_to_delete, self.user_id)
        self.assertEqual(delete_count, len(hids))

    def test__get_token_roles(self):
        self.start_test()
        handler = self.getHandler()

        customroles = handler._get_token_roles(self.token)

        self.assertTrue(isinstance(customroles, list))

    @patch.object(Handler, "_is_admin_user", return_value=True)
    def test_add_read_acl_ok(self, _is_admin_user):
        self.start_test()
        handler = self.getHandler()
        node_id = self.createTestNode()

        hids = list()

        handle = {'id': node_id,
                  'file_name': 'file_name',
                  'type': 'shock',
                  'url': self.shock_url}
        hid = handler.persist_handle(handle, self.user_id)
        hids.append(hid)

        headers = {'Authorization': 'OAuth {}'.format(self.token)}
        end_point = os.path.join(self.shock_url, 'node', node_id, 'acl/?verbosity=full')
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()

        # no public access at the beginning
        self.assertFalse(data.get('data').get('public').get('read'))

        # only token user has read access
        users = [user.get('username') for user in data.get('data').get('read')]
        self.assertCountEqual(users, [self.user_id])

        # grant public read access
        handler.add_read_acl(hids, self.token)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        self.assertTrue(data.get('data').get('public').get('read'))

        # should work for already publicly accessable ndoes
        handler.add_read_acl(hids, self.token)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        self.assertTrue(data.get('data').get('public').get('read'))

        # test grant access to user who already has read access
        handler.add_read_acl(hids, self.token, username=self.user_id)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        new_users = [user.get('username') for user in data.get('data').get('read')]
        self.assertCountEqual(new_users, [self.user_id])

        # grant access to tgu3
        new_user = 'tgu3'
        handler.add_read_acl(hids, self.token, username=new_user)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        new_users = [user.get('username') for user in data.get('data').get('read')]
        self.assertCountEqual(new_users, [self.user_id, new_user])

        handles_to_delete = handler.fetch_handles_by({'elements': hids, 'field_name': 'hid'})
        delete_count = handler.delete_handles(handles_to_delete, self.user_id)
        self.assertEqual(delete_count, len(hids))

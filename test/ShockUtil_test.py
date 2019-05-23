# -*- coding: utf-8 -*-
import os
import unittest
from configparser import ConfigParser
import inspect
import requests as _requests
from unittest.mock import patch

from AbstractHandle.authclient import KBaseAuth as _KBaseAuth
from AbstractHandle.Utils.ShockUtil import ShockUtil


class ShockUtilTest(unittest.TestCase):

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
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        cls.user_id = auth_client.get_user(cls.token)

        cls.shock_util = ShockUtil(cls.cfg)
        cls.shock_url = cls.cfg['shock-url']
        cls.shock_ids_to_delete = list()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'shock_ids_to_delete'):
            print('Nodes to delete: {}'.format(cls.shock_ids_to_delete))
            cls.deleteShockID(cls.shock_ids_to_delete)

        print('Finished testing ShockUtil')

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

    def getShockUtil(self):
        return self.__class__.shock_util

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

    def start_test(self):
        testname = inspect.stack()[1][3]
        print('\n*** starting test: ' + testname + ' **')

    def test_init_ok(self):
        self.start_test()
        class_attri = ['admin_token', 'shock_url']
        shock_util = self.getShockUtil()
        self.assertTrue(set(class_attri) <= set(shock_util.__dict__.keys()))

    @patch.object(ShockUtil, "SERVER_TYPE", new='fake_server_type')
    def test_init_fail(self):
        self.start_test()
        config = {'shock-url': self.shock_url + '/' + 'fake_endpoint_100'}
        with self.assertRaises(ValueError) as context:
            ShockUtil(config)
        self.assertIn('Connot connect to shock server', str(context.exception.args))

        config = {'shock-url': self.shock_url}
        with self.assertRaises(ValueError) as context:
            ShockUtil(config)
        self.assertIn('Unexpected response from shock server', str(context.exception.args))

    def test_get_owner_fail(self):
        self.start_test()
        shock_util = self.getShockUtil()

        node_id = 'fake_node_id'
        with self.assertRaises(ValueError) as context:
            shock_util.get_owner(node_id, self.token)

        self.assertIn('Request owner failed', str(context.exception.args))

    def test_get_owner_ok(self):
        self.start_test()
        shock_util = self.getShockUtil()
        node_id = self.createTestNode()

        owner = shock_util.get_owner(node_id, self.token)

        self.assertEqual(owner, self.user_id)

    def test_is_readable_ok(self):
        self.start_test()
        shock_util = self.getShockUtil()
        node_id = self.createTestNode()

        is_readable = shock_util.is_readable(node_id, self.token)
        self.assertTrue(is_readable)

        node_id = 'fake_node_id'
        is_readable = shock_util.is_readable(node_id, self.token)
        self.assertFalse(is_readable)

    def test_add_read_acl_ok(self):
        self.start_test()
        shock_util = self.getShockUtil()
        node_id = self.createTestNode()

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
        shock_util.add_read_acl(node_id, self.token)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        self.assertTrue(data.get('data').get('public').get('read'))

        # should work for already publicly accessable ndoes
        shock_util.add_read_acl(node_id, self.token)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        self.assertTrue(data.get('data').get('public').get('read'))

        # test grant access to user who already has read access
        shock_util.add_read_acl(node_id, self.token, username=self.user_id)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        new_users = [user.get('username') for user in data.get('data').get('read')]
        self.assertCountEqual(new_users, [self.user_id])

        # grant access to tgu3 (Tian made this test so ^^)
        new_user = 'tgu3'
        shock_util.add_read_acl(node_id, self.token, username=new_user)
        resp = _requests.get(end_point, headers=headers)
        data = resp.json()
        new_users = [user.get('username') for user in data.get('data').get('read')]
        self.assertCountEqual(new_users, [self.user_id, new_user])

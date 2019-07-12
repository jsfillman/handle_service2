
import logging
from time import gmtime, strftime
import os
import requests as _requests

from AbstractHandle.Utils.MongoUtil import MongoUtil
from AbstractHandle.Utils.ShockUtil import ShockUtil
from AbstractHandle.Utils.TokenCache import TokenCache


class Handler:

    FIELD_NAMES = ['hid', 'id', 'file_name', 'type', 'url', 'remote_md5', 'remote_sha1',
                   'created_by', 'creation_date']

    AUTH_API_PATH = 'api/V2'
    CACHE_EXPIRE_TIME = 300  # seconds

    @staticmethod
    def validate_params(params, expected, opt_param=set()):
        """Validates that required parameters are present. Warns if unexpected parameters appear"""
        expected = set(expected)
        opt_param = set(opt_param)
        pkeys = set(params)
        if expected - pkeys:
            raise ValueError("Required keys {} not in supplied parameters"
                             .format(", ".join(expected - pkeys)))
        defined_param = expected | opt_param
        for param in params:
            if param not in defined_param:
                logging.warning("Unexpected parameter {} supplied".format(param))

    def _process_handle(self, handle, user_id):
        """
        pre-process handle: check/remove/add fields
        """
        logging.info('start processing handle')

        handle = {k: v for k, v in handle.items() if k in self.FIELD_NAMES}  # remove unnecessary fields
        if not handle.get('hid'):
            hid_counter = self.mongo_util.get_hid_counter()
            handle['hid'] = str(hid_counter)
        else:
            handle['hid'] = handle['hid'].split(self.namespace + '_')[-1]

        handle['_id'] = int(handle['hid'])  # assign _id to 'hid'

        required_fields = ['id', 'type', 'url']
        fields_values = [v for k, v in handle.items() if k in required_fields]
        if (len(fields_values) != len(required_fields)) or (not all(fields_values)):
            error_msg = 'Missing one or more required positional field\n'
            error_msg += 'Requried fields: {}'.format(required_fields)
            raise ValueError(error_msg)

        if not handle.get('file_name'):  # assign None to remote_md5/remote_sha1 if missing/empty
            handle['file_name'] = None

        if not handle.get('remote_md5'):  # assign None to remote_md5/remote_sha1 if missing/empty
            handle['remote_md5'] = None

        if not handle.get('remote_sha1'):
            handle['remote_sha1'] = None

        if not handle.get('created_by'):  # assign created_by to current token user if missing
            handle['created_by'] = user_id

        if not handle.get('creation_date'):  # assign creation_date if missing
            handle['creation_date'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())

        return handle

    def _get_token_roles(self, token):

        headers = {'Authorization': token}
        end_point = os.path.join(self.auth_url, self.AUTH_API_PATH, 'me')

        resp = _requests.get(end_point, headers=headers)

        if resp.status_code != 200:
            raise ValueError('Request owner failed.\nError Code: {}\n{}\n'
                             .format(resp.status_code, resp.text))
        else:
            data = resp.json()
            customroles = data.get('customroles')
            return customroles

    def _is_admin_user(self, token):
        fetched_token_info = self.token_cache.get(token)

        if fetched_token_info:
            customroles = fetched_token_info.get('customroles')
        else:
            customroles = self._get_token_roles(token)
            self.token_cache[token] = {'customroles': customroles}

        return not set(self.admin_roles).isdisjoint(customroles)

    def __init__(self, config):
        self.mongo_util = MongoUtil(config)
        self.shock_util = ShockUtil(config)
        self.token_cache = TokenCache(1000, self.CACHE_EXPIRE_TIME)
        self.auth_url = config.get('auth-url')
        self.admin_roles = [role.strip() for role in config.get('admin-roles').split(',')]
        self.namespace = config.get('namespace')

        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)

    def fetch_handles_by(self, params):
        """
        query DB and return if element match one of entry in field column
        """
        logging.info('start fetching handles')

        self.validate_params(params, ['elements', 'field_name'])

        elements = params.get('elements')
        field_name = params.get('field_name')

        if field_name == 'hid':
            # remove prefix for hids
            elements = [hid.split(self.namespace + '_')[-1] for hid in elements]

        docs = self.mongo_util.find_in(elements, field_name)

        handles = list()
        for doc in docs:
            # append prefix for returned hids
            doc['hid'] = self.namespace + '_' + doc['hid']
            handles.append(doc)

        return handles

    def persist_handle(self, handle, user_id):
        """
        writes the handle to a persistent store

        insert handle if handle does not exist
        otherwise update handle if it's created by token user
        """
        logging.info('start persisting handle')

        handle = self._process_handle(handle, user_id)
        hid = handle.get('hid')

        docs = self.mongo_util.find_in([hid], 'hid')

        if docs.count():
            # handle exists, update handle
            if handle.get('created_by') != user_id:
                raise ValueError('Cannot update handle not created by owner')

            self.mongo_util.update_one(handle)
        else:
            # handle doesn't exist, insert handle
            self.mongo_util.insert_one(handle)

        return str(self.namespace + '_' + hid)

    def delete_handles(self, handles, user_id):
        """
        delete handles

        raise error if any of handles are not created by token user
        """

        handle_user = set([h.get('created_by') for h in handles])

        if not (handle_user == set([user_id])):
            raise ValueError('Cannot delete handles not created by owner')

        # remove 'KBH_' prefix for hids
        for handle in handles:
            handle['hid'] = handle['hid'].split(self.namespace + '_')[-1]

        deleted_count = self.mongo_util.delete_many(handles)

        return deleted_count

    def is_owner(self, hids, token, user_id):
        """
        check and see if token user is owner.username from shock node
        """

        # remove 'KBH_' prefix for hids
        hids = [hid.split(self.namespace + '_')[-1] for hid in hids]

        handles = self.fetch_handles_by({'elements': hids, 'field_name': 'hid'})

        for handle in handles:
            node_type = handle.get('type')
            if node_type != 'shock':
                raise ValueError('Do not support node type other than Shock')

            node_id = handle.get('id')
            owner = self.shock_util.get_owner(node_id, token)

            if owner != user_id:
                return 0

        return 1

    def are_readable(self, hids, token):
        """
        check if nodes associated with handles is reachable/readable
        """

        # remove 'KBH_' prefix for hids
        hids = [hid.split(self.namespace + '_')[-1] for hid in hids]

        handles = self.fetch_handles_by({'elements': hids, 'field_name': 'hid'})

        for handle in handles:
            node_type = handle.get('type')
            if node_type != 'shock':
                raise ValueError('Do not support node type other than Shock')

            node_id = handle.get('id')

            is_readable = self.shock_util.is_readable(node_id, token)

            if not is_readable:
                return 0

        return 1

    def add_read_acl(self, hids, token, username=None):
        """
        grand readable acl for username or global if username is empty
        """

        # remove 'KBH_' prefix for hids
        hids = [hid.split(self.namespace + '_')[-1] for hid in hids]

        if not self._is_admin_user(token):
            raise ValueError('User may not run add_read_acl/set_public_read method')

        handles = self.fetch_handles_by({'elements': hids, 'field_name': 'hid'})

        for handle in handles:
            node_type = handle.get('type')
            if node_type != 'shock':
                raise ValueError('Do not support node type other than Shock')

            node_id = handle.get('id')
            try:
                self.shock_util.add_read_acl(node_id, token, username=username)
            except Exception:
                raise ValueError("Unable to set acl(s) on handles {}".format(handle.get('hid')))

        return 1

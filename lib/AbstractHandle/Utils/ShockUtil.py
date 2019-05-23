
import logging
import os
import traceback
import requests as _requests


class ShockUtil:

    SERVER_TYPE = 'Shock'

    def _get_header(self, token):
        return {'Authorization': 'OAuth {}'.format(token)}

    def _get_admin_header(self):
        return {'Authorization': 'OAuth {}'.format(self.admin_token)}

    def _grant_read_access(self, node_id, token, username=None):
        """
        grant readable acl for username or global if username is empty
        """
        headers = self._get_header(token)

        if username:  # grand readable acl for user
            end_point = os.path.join(self.shock_url, 'node', node_id, 'acl/read?users={}'.format(username))
            resp = _requests.put(end_point, headers=headers)

            if resp.status_code != 200:
                raise ValueError('Grant user readable access failed.\nError Code: {}\n{}\n'
                                 .format(resp.status_code, resp.text))
            else:
                return True
        else:  # grand global readable acl
            end_point = os.path.join(self.shock_url, 'node', node_id, 'acl/public_read')
            resp = _requests.put(end_point, headers=headers)

            if resp.status_code != 200:
                raise ValueError('Grant global readable access failed.\nError Code: {}\n{}\n'
                                 .format(resp.status_code, resp.text))
            else:
                return True

    def _check_shock_conn(self, shock_url):
        end_point = self.shock_url + '/'
        resp = _requests.put(end_point)

        if resp.status_code != 200:
            raise ValueError('Connot connect to shock server.\nError Code: {}\n{}\n'
                             .format(resp.status_code, resp.text))
        else:
            data = resp.json()
            if data.get('type') != self.SERVER_TYPE or data.get('url') != end_point:
                raise ValueError('Unexpected response from shock server.\nError Code: {}\n{}\n'
                                 .format(resp.status_code, resp.text))

    def __init__(self, config):
        self.shock_url = config.get('shock-url')
        self.admin_token = config.get('admin-token')

        self._check_shock_conn(self.shock_url)

        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)

    def get_owner(self, node_id, token):
        """
        parse owner.username information from shock acl of a node
        """

        headers = self._get_header(token)

        end_point = os.path.join(self.shock_url, 'node', node_id, 'acl/?verbosity=full')

        resp = _requests.get(end_point, headers=headers)

        if resp.status_code != 200:
            raise ValueError('Request owner failed.\nError Code: {}\n{}\n'
                             .format(resp.status_code, resp.text))
        else:
            data = resp.json()
            try:
                owner = data.get('data').get('owner').get('username')
            except Exception as e:
                error_msg = 'Connot parse owner information from reponse\n'
                error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
                raise ValueError(error_msg)
            else:
                return owner

    def is_readable(self, node_id, token):
        """
        check if a node is reachable/readable
        """

        headers = self._get_header(token)

        end_point = os.path.join(self.shock_url, 'node', node_id)

        resp = _requests.get(end_point, headers=headers)

        if resp.ok:
            return True
        else:
            return False

    def add_read_acl(self, node_id, token, username=None):
        """
        check current acl and then grant readable acl to user or public
        """

        headers = self._get_admin_header()

        end_point = os.path.join(self.shock_url, 'node', node_id, 'acl/?verbosity=full')
        resp = _requests.get(end_point, headers=headers)

        if resp.status_code != 200:
            raise ValueError('Grant readable access for node failed.\nError Code: {}\n{}\n'
                             .format(resp.status_code, resp.text))
        else:
            data = resp.json()

            if username:  # check readble acl and grand readable acl for user
                try:
                    read_users = data.get('data').get('read')
                except Exception as e:
                    error_msg = 'Connot parse read information from reponse\n'
                    error_msg += 'ERROR -- {}:\n{}'.format(
                                e,
                                ''.join(traceback.format_exception(None, e, e.__traceback__)))
                    raise ValueError(error_msg)
                else:
                    read_users = [r.get('username') for r in read_users]

                    if username not in read_users:
                        # grant user read access
                        self._grant_read_access(node_id, token, username=username)
            else:  # check readble acl and grand global readable acl
                try:
                    public_read = data.get('data').get('public').get('read')
                except Exception as e:
                    error_msg = 'Connot parse public_read information from reponse\n'
                    error_msg += 'ERROR -- {}:\n{}'.format(
                                e,
                                ''.join(traceback.format_exception(None, e, e.__traceback__)))
                    raise ValueError(error_msg)
                else:
                    if not public_read:
                        # grant global read access
                        self._grant_read_access(node_id, token)

        return True

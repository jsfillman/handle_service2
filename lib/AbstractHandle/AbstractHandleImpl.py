# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging

from AbstractHandle.Utils.Handler import Handler
#END_HEADER


class AbstractHandle:
    '''
    Module Name:
    AbstractHandle

    Module Description:
    A KBase module: AbstractHandle
provides a programmatic access to a remote file store
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "1.0.0"
    GIT_URL = "git@github.com:Tianhao-Gu/handle_service2.git"
    GIT_COMMIT_HASH = "97517349590de76e4cc306bf3a93556fbea2684b"

    #BEGIN_CLASS_HEADER
    MONGO_COLLECTION = 'handle'
    MONGO_HID_COUNTER_COLLECTION = 'handle_id_counter'
    MONGO_AUTHMECHANISM = 'DEFAULT'
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.config = config
        self.config['mongo-collection'] = self.MONGO_COLLECTION
        self.config['mongo-hid-counter-collection'] = self.MONGO_HID_COUNTER_COLLECTION
        self.config.setdefault('mongo-authmechanism', self.MONGO_AUTHMECHANISM)

        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)

        self.handler = Handler(self.config)
        #END_CONSTRUCTOR
        pass


    def persist_handle(self, ctx, handle):
        """
        The persist_handle writes the handle to a persistent store that can be later retrieved using the list_handles function.
        :param handle: instance of type "Handle" -> structure: parameter
           "hid" of type "HandleId" (Handle provides a unique reference that
           enables access to the data files through functions provided as
           part of the HandleService. In the case of using shock, the id is
           the node id. In the case of using shock the value of type is
           shock. In the future these values should enumerated. The value of
           url is the http address of the shock server, including the
           protocol (http or https) and if necessary the port. The values of
           remote_md5 and remote_sha1 are those computed on the file in the
           remote data store. These can be used to verify uploads and
           downloads.), parameter "file_name" of String, parameter "id" of
           type "NodeId", parameter "type" of String, parameter "url" of
           String, parameter "remote_md5" of String, parameter "remote_sha1"
           of String
        :returns: instance of String
        """
        # ctx is the context object
        # return variables are: hid
        #BEGIN persist_handle
        logging.info("Start persist handle")

        hid = self.handler.persist_handle(handle, ctx['user_id'])
        #END persist_handle

        # At some point might do deeper type checking...
        if not isinstance(hid, str):
            raise ValueError('Method persist_handle return value ' +
                             'hid is not type str as required.')
        # return the results
        return [hid]

    def hids_to_handles(self, ctx, hids):
        """
        Given a list of handle ids, this function returns a list of handles.
        This method is replaced by fetch_handles_by.
        :param hids: instance of list of type "HandleId" (Handle provides a
           unique reference that enables access to the data files through
           functions provided as part of the HandleService. In the case of
           using shock, the id is the node id. In the case of using shock the
           value of type is shock. In the future these values should
           enumerated. The value of url is the http address of the shock
           server, including the protocol (http or https) and if necessary
           the port. The values of remote_md5 and remote_sha1 are those
           computed on the file in the remote data store. These can be used
           to verify uploads and downloads.)
        :returns: instance of list of type "Handle" -> structure: parameter
           "hid" of type "HandleId" (Handle provides a unique reference that
           enables access to the data files through functions provided as
           part of the HandleService. In the case of using shock, the id is
           the node id. In the case of using shock the value of type is
           shock. In the future these values should enumerated. The value of
           url is the http address of the shock server, including the
           protocol (http or https) and if necessary the port. The values of
           remote_md5 and remote_sha1 are those computed on the file in the
           remote data store. These can be used to verify uploads and
           downloads.), parameter "file_name" of String, parameter "id" of
           type "NodeId", parameter "type" of String, parameter "url" of
           String, parameter "remote_md5" of String, parameter "remote_sha1"
           of String
        """
        # ctx is the context object
        # return variables are: handles
        #BEGIN hids_to_handles
        handles = self.fetch_handles_by(ctx, {'elements': hids, 'field_name': 'hid'})[0]
        #END hids_to_handles

        # At some point might do deeper type checking...
        if not isinstance(handles, list):
            raise ValueError('Method hids_to_handles return value ' +
                             'handles is not type list as required.')
        # return the results
        return [handles]

    def ids_to_handles(self, ctx, ids):
        """
        Given a list of ids, this function returns a list of handles.
        In case of Shock, the list of ids are shock node ids.
        This method is replaced by fetch_handles_by.
        :param ids: instance of list of type "NodeId"
        :returns: instance of list of type "Handle" -> structure: parameter
           "hid" of type "HandleId" (Handle provides a unique reference that
           enables access to the data files through functions provided as
           part of the HandleService. In the case of using shock, the id is
           the node id. In the case of using shock the value of type is
           shock. In the future these values should enumerated. The value of
           url is the http address of the shock server, including the
           protocol (http or https) and if necessary the port. The values of
           remote_md5 and remote_sha1 are those computed on the file in the
           remote data store. These can be used to verify uploads and
           downloads.), parameter "file_name" of String, parameter "id" of
           type "NodeId", parameter "type" of String, parameter "url" of
           String, parameter "remote_md5" of String, parameter "remote_sha1"
           of String
        """
        # ctx is the context object
        # return variables are: handles
        #BEGIN ids_to_handles
        handles = self.fetch_handles_by(ctx, {'elements': ids, 'field_name': 'id'})[0]
        #END ids_to_handles

        # At some point might do deeper type checking...
        if not isinstance(handles, list):
            raise ValueError('Method ids_to_handles return value ' +
                             'handles is not type list as required.')
        # return the results
        return [handles]

    def fetch_handles_by(self, ctx, params):
        """
        This function select records if field column entry is in elements and returns a list of handles.
        :param params: instance of type "FetchHandlesParams" -> structure:
           parameter "elements" of list of String, parameter "field_name" of
           String
        :returns: instance of list of type "Handle" -> structure: parameter
           "hid" of type "HandleId" (Handle provides a unique reference that
           enables access to the data files through functions provided as
           part of the HandleService. In the case of using shock, the id is
           the node id. In the case of using shock the value of type is
           shock. In the future these values should enumerated. The value of
           url is the http address of the shock server, including the
           protocol (http or https) and if necessary the port. The values of
           remote_md5 and remote_sha1 are those computed on the file in the
           remote data store. These can be used to verify uploads and
           downloads.), parameter "file_name" of String, parameter "id" of
           type "NodeId", parameter "type" of String, parameter "url" of
           String, parameter "remote_md5" of String, parameter "remote_sha1"
           of String
        """
        # ctx is the context object
        # return variables are: handles
        #BEGIN fetch_handles_by
        handles = self.handler.fetch_handles_by(params)
        #END fetch_handles_by

        # At some point might do deeper type checking...
        if not isinstance(handles, list):
            raise ValueError('Method fetch_handles_by return value ' +
                             'handles is not type list as required.')
        # return the results
        return [handles]

    def is_owner(self, ctx, hids):
        """
        Given a list of handle ids, this function determines if the underlying data is owned by the caller.
        If any one of the handle ids reference unreadable data this function returns false.
        :param hids: instance of list of type "HandleId" (Handle provides a
           unique reference that enables access to the data files through
           functions provided as part of the HandleService. In the case of
           using shock, the id is the node id. In the case of using shock the
           value of type is shock. In the future these values should
           enumerated. The value of url is the http address of the shock
           server, including the protocol (http or https) and if necessary
           the port. The values of remote_md5 and remote_sha1 are those
           computed on the file in the remote data store. These can be used
           to verify uploads and downloads.)
        :returns: instance of Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN is_owner
        returnVal = self.handler.is_owner(hids, ctx['token'], ctx['user_id'])
        #END is_owner

        # At some point might do deeper type checking...
        if not isinstance(returnVal, int):
            raise ValueError('Method is_owner return value ' +
                             'returnVal is not type int as required.')
        # return the results
        return [returnVal]

    def delete_handles(self, ctx, handles):
        """
        The delete_handles function takes a list of handles and deletes them on the handle service server.
        :param handles: instance of list of type "Handle" -> structure:
           parameter "hid" of type "HandleId" (Handle provides a unique
           reference that enables access to the data files through functions
           provided as part of the HandleService. In the case of using shock,
           the id is the node id. In the case of using shock the value of
           type is shock. In the future these values should enumerated. The
           value of url is the http address of the shock server, including
           the protocol (http or https) and if necessary the port. The values
           of remote_md5 and remote_sha1 are those computed on the file in
           the remote data store. These can be used to verify uploads and
           downloads.), parameter "file_name" of String, parameter "id" of
           type "NodeId", parameter "type" of String, parameter "url" of
           String, parameter "remote_md5" of String, parameter "remote_sha1"
           of String
        :returns: instance of Long
        """
        # ctx is the context object
        # return variables are: deleted_count
        #BEGIN delete_handles
        deleted_count = self.handler.delete_handles(handles, ctx['user_id'])
        #END delete_handles

        # At some point might do deeper type checking...
        if not isinstance(deleted_count, int):
            raise ValueError('Method delete_handles return value ' +
                             'deleted_count is not type int as required.')
        # return the results
        return [deleted_count]

    def are_readable(self, ctx, hids):
        """
        Given a list of handle ids, this function determines if the underlying data is readable by the caller.
        If any one of the handle ids reference unreadable data this function returns false.
        :param hids: instance of list of type "HandleId" (Handle provides a
           unique reference that enables access to the data files through
           functions provided as part of the HandleService. In the case of
           using shock, the id is the node id. In the case of using shock the
           value of type is shock. In the future these values should
           enumerated. The value of url is the http address of the shock
           server, including the protocol (http or https) and if necessary
           the port. The values of remote_md5 and remote_sha1 are those
           computed on the file in the remote data store. These can be used
           to verify uploads and downloads.)
        :returns: instance of Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN are_readable
        returnVal = self.handler.are_readable(hids, ctx['token'])
        #END are_readable

        # At some point might do deeper type checking...
        if not isinstance(returnVal, int):
            raise ValueError('Method are_readable return value ' +
                             'returnVal is not type int as required.')
        # return the results
        return [returnVal]

    def is_readable(self, ctx, hid):
        """
        Given a handle id, this function queries the underlying data store to see if the data being referred to is readable to by the caller.
        :param hid: instance of type "HandleId" (Handle provides a unique
           reference that enables access to the data files through functions
           provided as part of the HandleService. In the case of using shock,
           the id is the node id. In the case of using shock the value of
           type is shock. In the future these values should enumerated. The
           value of url is the http address of the shock server, including
           the protocol (http or https) and if necessary the port. The values
           of remote_md5 and remote_sha1 are those computed on the file in
           the remote data store. These can be used to verify uploads and
           downloads.)
        :returns: instance of Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN is_readable
        returnVal = self.are_readable(ctx, [hid])[0]
        #END is_readable

        # At some point might do deeper type checking...
        if not isinstance(returnVal, int):
            raise ValueError('Method is_readable return value ' +
                             'returnVal is not type int as required.')
        # return the results
        return [returnVal]

    def add_read_acl(self, ctx, hids, username):
        """
        The add_read_acl function will update the acl of the shock node that the handle references.
        The function is only accessible to a specific list of users specified at startup time.
        The underlying shock node will be made readable to the user requested.
        :param hids: instance of list of type "HandleId" (Handle provides a
           unique reference that enables access to the data files through
           functions provided as part of the HandleService. In the case of
           using shock, the id is the node id. In the case of using shock the
           value of type is shock. In the future these values should
           enumerated. The value of url is the http address of the shock
           server, including the protocol (http or https) and if necessary
           the port. The values of remote_md5 and remote_sha1 are those
           computed on the file in the remote data store. These can be used
           to verify uploads and downloads.)
        :param username: instance of String
        :returns: instance of Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN add_read_acl
        returnVal = self.handler.add_read_acl(hids, ctx['token'], username=username)
        #END add_read_acl

        # At some point might do deeper type checking...
        if not isinstance(returnVal, int):
            raise ValueError('Method add_read_acl return value ' +
                             'returnVal is not type int as required.')
        # return the results
        return [returnVal]

    def set_public_read(self, ctx, hids):
        """
        The set_public_read function will update the acl of the shock node that the handle references to make the node globally readable.
        The function is only accessible to a specific list of users specified at startup time.
        :param hids: instance of list of type "HandleId" (Handle provides a
           unique reference that enables access to the data files through
           functions provided as part of the HandleService. In the case of
           using shock, the id is the node id. In the case of using shock the
           value of type is shock. In the future these values should
           enumerated. The value of url is the http address of the shock
           server, including the protocol (http or https) and if necessary
           the port. The values of remote_md5 and remote_sha1 are those
           computed on the file in the remote data store. These can be used
           to verify uploads and downloads.)
        :returns: instance of Long
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN set_public_read
        returnVal = self.handler.add_read_acl(hids, ctx['token'])
        #END set_public_read

        # At some point might do deeper type checking...
        if not isinstance(returnVal, int):
            raise ValueError('Method set_public_read return value ' +
                             'returnVal is not type int as required.')
        # return the results
        return [returnVal]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]

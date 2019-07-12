#!/usr/bin/python


import mysql.connector

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.errors import BulkWriteError

import traceback
import sys
import getopt


def connect_mysql(sql_server, sql_username, sql_password, sql_database):

    my_sqldb = mysql.connector.connect(
      host=sql_server,
      user=sql_username,
      passwd=sql_password,
      database=sql_database
    )

    return my_sqldb


def connect_mongo(mongo_host, mongo_port, mongo_database, mongo_collection,
                  mongo_username=None, mongo_password=None, mongo_authmechanism='DEFAULT'):

    if mongo_username:
        print('mongo_user supplied, configuring client for authentication using mech ' + str(mongo_authmechanism) )
        my_client = MongoClient(mongo_host, mongo_port,
                                username=mongo_username, password=mongo_password,
                                authSource=mongo_database,
                                authMechanism=mongo_authmechanism)
    else:
        print('no mongo_user supplied, connecting without auth')
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


def insert_one(my_collection, doc):

    result = my_collection.find({'hid': {'$in': [doc.get('hid')]}}, projection=None)

    if not result.count():
        try:
            my_collection.insert_one(doc)
        except Exception as e:
            error_msg = 'Connot insert doc\n'
            error_msg += 'ERROR -- {}:\n{}'.format(
                            e,
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
            raise ValueError(error_msg)
        else:
            return True
    else:
        return False


def main(argv):

    input_args = ['sql_server', 'sql_username', 'sql_password', 'mongo_host',
                  'mongo_username', 'mongo_password', 'mongo_authmechanism']
    sql_server = ''
    sql_username = ''
    sql_password = ''
    mongo_host = ''
    mongo_username = None
    mongo_password = None
    mongo_authmechanism = 'DEFAULT'

    usage_string = 'mysql_to_mongo.py --sql_server <sql_server> --sql_username <sql_username> --sql_password <sql_password> --mongo_host <mongo_host> [ --mongo_username <mongo_username> --mongo_password <mongo_password> [ --mongo_authmechanism <mongo_authmechanism> ] ]'

    try:
        opts, args = getopt.getopt(argv, "h", [a + '=' for a in input_args])
    except getopt.GetoptError:
        print('unrecognized option provided')
        print(usage_string)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(usage_string)
            sys.exit()
        elif opt == '--sql_server':
            sql_server = arg
        elif opt == '--sql_username':
            sql_username = arg
        elif opt == '--sql_password':
            sql_password = arg
        elif opt == '--mongo_host':
            mongo_host = arg
        elif opt == '--mongo_username':
            mongo_username = arg
        elif opt == '--mongo_password':
            mongo_password = arg
        elif opt == '--mongo_authmechanism':
            mongo_authmechanism = arg

    if not all([sql_server, sql_username, sql_password, mongo_host]):
        print('missing one of requried args')
        print(usage_string)
        sys.exit()

    sql_port = 3306
    sql_database = 'hsi'

    my_sqldb = connect_mysql(sql_server, sql_username, sql_password, sql_database)
    mycursor = my_sqldb.cursor()

    mongo_port = 27017
    mongo_database = 'handle_db'
    mongo_collection = 'handle'
    mongo_counter_collection = 'handle_id_counter'
    my_collection = connect_mongo(mongo_host, mongo_port, mongo_database, mongo_collection, mongo_username, mongo_password, mongo_authmechanism)
    counter_collection = connect_mongo(mongo_host, mongo_port, mongo_database, mongo_counter_collection, mongo_username, mongo_password, mongo_authmechanism)

    mycursor.execute("SELECT COUNT(*) FROM Handle")
    myresult = mycursor.fetchall()
    total_records = myresult[0][0]
    print('total MySQL record count: {}'.format(total_records))

    mycursor.execute("SELECT * FROM Handle")

    columns = ['hid', 'id', 'file_name', 'type', 'url', 'remote_md5', 'remote_sha1',
               'created_by', 'creation_date']

    insert_records = 0
    max_counter = 0
    doc_insert_list = []

    for x in mycursor:
        doc = dict(zip(columns, x))
        hid = doc['hid']
        doc['_id'] = hid

        doc_insert_list.append(doc)
        
        if len(doc_insert_list) % 5000 == 0:
            try:
                insert_result = my_collection.insert_many(doc_insert_list,ordered=False)
            except BulkWriteError as bwe:
                print(bwe.details)
            print ('inserted {} records'.format(len(insert_result.inserted_ids)))
            doc_insert_list = []

# do one final bulk insert
    try:
        insert_result = my_collection.insert_many(doc_insert_list,ordered=False)
    except BulkWriteError as bwe:
        print(bwe.details)
    print ('inserted {} records'.format(len(insert_result.inserted_ids)))
    doc_insert_list = []

# get the max_id from the handle collection itself instead of from the mysql ids
    max_id = my_collection.find_one( sort = [("_id", -1)] )["_id"]
    print ( max_id )
    
    counter_collection.delete_many({})
    counter_collection.insert_one({'_id': 'hid_counter', 'hid_counter': max_id + 1})

    print('max id: {} '.format(max_id))


if __name__ == "__main__":
    main(sys.argv[1:])

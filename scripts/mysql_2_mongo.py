#!/usr/bin/python


import mysql.connector
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
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


def connect_mongo(mongo_host, mongo_port, mongo_database, mongo_collection):
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

    input_args = ['sql_server', 'sql_username', 'sql_password', 'mongo_host']
    sql_server = ''
    sql_username = ''
    sql_password = ''
    mongo_host = ''

    try:
        opts, args = getopt.getopt(argv, "h", [a + '=' for a in input_args])
    except getopt.GetoptError:
        print('mysql_to_mongo.py --sql_server <sql_server> --sql_username <sql_username> --sql_password <sql_password> --mongo_host <mongo_host>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('mysql_to_mongo.py --sql_server <sql_server> --sql_username <sql_username> --sql_password <sql_password> --mongo_host <mongo_host>')
            sys.exit()
        elif opt == '--sql_server':
            sql_server = arg
        elif opt == '--sql_username':
            sql_username = arg
        elif opt == '--sql_password':
            sql_password = arg
        elif opt == '--mongo_host':
            mongo_host = arg

    if not all([sql_server, sql_username, sql_password, mongo_host]):
        print('missing one of requried args')
        print('mysql_to_mongo.py --sql_server <sql_server> --sql_username <sql_username> --sql_password <sql_password> --mongo_host <mongo_host>')
        sys.exit()

    sql_port = 3306
    sql_database = 'hsi'

    my_sqldb = connect_mysql(sql_server, sql_username, sql_password, sql_database)
    mycursor = my_sqldb.cursor()

    mongo_port = 27017
    mongo_database = 'handle_db'
    mongo_collection = 'handle'
    mongo_counter_collection = 'handle_id_counter'
    my_collection = connect_mongo(mongo_host, mongo_port, mongo_database, mongo_collection)
    counter_collection = connect_mongo(mongo_host, mongo_port, mongo_database, mongo_counter_collection)

    mycursor.execute("SELECT COUNT(*) FROM Handle")
    myresult = mycursor.fetchall()
    total_records = myresult[0][0]
    print('total MySQL record count: {}'.format(total_records))

    mycursor.execute("SELECT * FROM Handle")
    myresult = mycursor.fetchall()

    columns = ['hid', 'id', 'file_name', 'type', 'url', 'remote_md5', 'remote_sha1',
               'created_by', 'creation_date']

    insert_records = 0
    max_counter = 0
    for x in myresult:
        doc = dict(zip(columns, x))
        hid = doc['hid']
        doc['_id'] = hid
        counter_str = hid.split('KBH_')[-1]
        try:
            counter = int(counter_str)
        except Exception:
            counter = 0

        if counter > max_counter:
            max_counter = counter

        if insert_one(my_collection, doc):
            insert_records += 1

        if insert_records/5000 == 0:
            print('inserted {} records'.format(insert_records))

    counter_collection.delete_many({})
    counter_collection.insert_one({'_id': 'hid_counter', 'hid_counter': max_counter + 1})

    print('totally inserted {} records'.format(insert_records))
    print('largest counter'.format(max_counter))


if __name__ == "__main__":
    main(sys.argv[1:])

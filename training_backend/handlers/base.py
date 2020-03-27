import rethinkdb as rdb
import logging
from tornado import gen
r = rdb.RethinkDB()
MY_HOST = "172.17.0.2"
MY_DB = "todo"

def setup_db(tables):
    logging.info("Setting up database and tables")

    connection = r.connect(host=MY_HOST)
    try:
        r.db_create(MY_DB).run(connection)
    except r.RqlRuntimeError:
        logging.warn("DB: %s already exists!" % MY_DB)

    for tbl in tables:
        try:
            r.db(MY_DB).table_create(tbl, durability="hard").run(connection)
            logging.info("%s created." % tbl)
        except r.RqlRuntimeError:
            logging.warn("%s already exists!" % tbl)

    logging.info('Database setup completed.')
    connection.close()

import tornado.ioloop
import tornado.web
from tornado import gen
import rethinkdb as rdb 
from handlers.base import setup_db,MY_HOST,MY_DB
r = rdb.RethinkDB()

class UserHandler(tornado.web.RequestHandler):

    @gen.coroutine
    def get(self):
        self.set_header('Content-Type', 'text/html')
        with open("./dist/index.html") as f:
            self.write(f.read())
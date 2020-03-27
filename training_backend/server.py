import tornado.ioloop
import tornado.web
import logging
import rethinkdb as rdb
from tornado import gen
from tornado.ioloop import IOLoop
from tornado import httpserver
from handlers.base import setup_db,MY_HOST,MY_DB
from handlers.UsercreateHandler import UsercreateHandler
from handlers.UserHandler import UserHandler
r = rdb.RethinkDB()

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")
    
class TodoApp(tornado.web.Application):
    def __init__(self, conn):
        handlers = [
            (r"/", IndexHandler),
            (r"/users", UsercreateHandler),
            (r"/user", UserHandler),
            (r"/assets/(.*)", tornado.web.StaticFileHandler, {
                'path' : 'dist/assets'
            })
        ]
        settings = dict(
            debug=True,
            template_path="dist",
        )
        self.conn = conn
        tornado.web.Application.__init__(self, handlers, **settings)

@gen.coroutine
def main():
    todo_tables = ["todo", "uploads","register","user"]
    setup_db(todo_tables)
    r.set_loop_type('tornado')
    conn = (yield r.connect(MY_HOST, db=MY_DB)).repl()
    http_server = httpserver.HTTPServer(TodoApp(conn))
    http_server.listen(8888)

if __name__ == "__main__":
    IOLoop.current().run_sync(main)
    IOLoop.current().start()
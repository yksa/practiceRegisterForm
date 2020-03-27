import tornado.ioloop
import tornado.web
import logging
import rethinkdb as r
from tornado import gen
from tornado.ioloop import IOLoop
from tornado import httpserver
from modules.handlers import (MY_HOST, MY_DB, IndexHandler, TodoHandler,
    setup_db, DoneHandler, EditHandler, EventHandler
)
from modules.upload import UploadHandler, UploadRemover


logging.basicConfig(level=10)


class TodoApp(tornado.web.Application):
    def __init__(self, conn):
        handlers = [
            (r"/", IndexHandler),
            (r"/todos", TodoHandler),
            (r"/todos/(\S+)", TodoHandler),
            (r"/done", DoneHandler),
            (r"/edit", EditHandler),
	        (r"/upload", UploadHandler),
            (r"/upload/remove", UploadRemover),
            (r"/todo/changes", EventHandler),
            (r"/contents/uploads/(.*)", tornado.web.StaticFileHandler, {
                'path': 'uploads'
            }),
            (r"/assets/(.*)", tornado.web.StaticFileHandler, {
                'path' : 'dist/assets'
            })
        ]
        settings = dict(
            debug=True,
            template_path="dist"
        )
        self.conn = conn
        tornado.web.Application.__init__(self, handlers, **settings)

@gen.coroutine
def main():
    todo_tables = ["todo", "uploads"]
    setup_db(todo_tables)
    r.set_loop_type('tornado')
    conn = (yield r.connect(MY_HOST, db=MY_DB)).repl()
    http_server = httpserver.HTTPServer(TodoApp(conn))
    http_server.listen(8989)


if __name__ == "__main__":
    IOLoop.current().run_sync(main)
    IOLoop.current().start()

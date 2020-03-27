import tornado.web
import logging
import rethinkdb as r
from tornado import gen

MY_HOST = "localhost"
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


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.conn = self.application.conn
        self.uploads = r.table("uploads")


class EventSourceHandler(BaseHandler):
    def set_default_headers(self):

        self.set_header("Server", "TornadoServer/%s" % tornado.version)
        self.set_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')
        self.set_header('access-control-allow-origin', "*")

    def write_events(self, name=None, data=True, wait=None, evt_id=None):
        to_send = ""
        if wait:
            to_send += "\nretry: %s" % wait
        if name:
            to_send += """\nevent: {name}""".format(name=name)
        if evt_id:
            to_send += """\nid: {evt_id}""".format(evt_id=evt_id)

        if isinstance(data, str) or isinstance(data, unicode):
            for line in data.splitlines(False):
                to_send += """\ndata: {data}""".format(data=line)
        elif isinstance(data, dict):
            to_send += """\ndata: {data}""".format(
                data=tornado.escape.json_encode(data))

        else:
            to_send += """\ndata: {data}""".format(data=data)

        to_send += "\n\n"
        self.write(to_send)
        self.flush()


class IndexHandler(BaseHandler):
    def get(self):
        self.render("index.html")


class TodoHandler(BaseHandler):
    @gen.coroutine
    def get(self, todo_id=None):
        rows = None
        completed = self.get_argument("completed", None) != "false"
        if todo_id:
            rows = yield r.table("todo").filter(dict(id=todo_id)).order_by('title').run(self.conn)
        else:
            rows = yield r.table("todo").filter(dict(completed = completed)).order_by('title').run(self.conn)
        self.write(dict(todo=rows))

    @gen.coroutine
    def post(self):
        # logging.debug(self.request.body)
        data = tornado.escape.json_decode(self.request.body)
        result = yield r.table('todo').insert(data.get("todo")).run(self.conn)
        self.write(result)

    @gen.coroutine
    def delete(self,todo_id=None):
        result = yield r.table("todo").filter(dict(id=todo_id)).delete().run(self.conn)
        self.write(result)

    @gen.coroutine
    def put(self,todo_id=None):
        data = tornado.escape.json_decode(self.request.body)
        result = yield r.table("todo").filter(dict(id=todo_id)).update(data.get('todo')).run(self.conn)
        self.write(result)


class DoneHandler(BaseHandler):
    @gen.coroutine
    def get(self, todo_id=None):
        rows = None
        completed = self.get_argument("completed", None) != "true"
        if todo_id:
            rows = yield r.table("todo").filter(dict(id=todo_id)).order_by('title').run(self.conn)
        else:
            rows = yield r.table("todo").filter(dict(completed = completed)).order_by('title').run(self.conn)
        self.write(dict(todo=rows))

    @gen.coroutine
    def put(self,todo_id=None):
        data = tornado.escape.json_decode(self.request.body)
        result = yield r.table("todo").filter(dict(id=todo_id)).update(data.get('todo')).run(self.conn)
        self.write(result)

    @gen.coroutine
    def delete(self,todo_id=None):
        result = yield r.table("todo").filter(dict(id=todo_id)).delete().run(self.conn)
        self.write(result)


class EditHandler(BaseHandler):
    @gen.coroutine
    def put(self,todo_id=None):
        data = tornado.escape.json_decode(self.request.body)
        result = yield r.table("todo").filter(dict(id=todo_id)).update(data.get('todo')).run(self.conn)
        self.write(result)


class EventHandler(EventSourceHandler):
    @gen.coroutine
    def get(self):
        changed = (yield r.table("todo").filter(r.row['event'] != None)
            .changes()
            .run(self.conn))
        while(yield changed.fetch_next()):
            feed = yield changed.next()
            # print feed
            if feed['new_val']:
                self.write_events(evt_id = feed['new_val']['id'],
                    name = feed['new_val']['event'],
                    data = feed['new_val']
                )
            else:
                self.write_events(evt_id = feed['old_val']['id'],
                    name = 'todoDeleted',
                    data = feed['old_val']
                )

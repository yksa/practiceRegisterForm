import tornado.ioloop
import tornado.web
from tornado import gen
import rethinkdb as rdb 
from handlers.base import setup_db,MY_HOST,MY_DB
r = rdb.RethinkDB()

class UsercreateHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        print('hello')
        data = tornado.escape.json_decode(self.request.body)
        print(data["user"])
        x =yield r.table('user').insert(data["user"], return_changes=True).run()
        data = x['changes'][0]["new_val"]
        print (data)
        self.write(dict(user = data))
        
    @gen.coroutine
    def get(self):
        data = yield r.table('user').order_by('id').run(time_format="raw")
        print(data)
        self.write(dict(user=data))

import tornado.web
import os
# import datetime
# import logging
import tempfile
# import mimetypes
import json
import rethinkdb as r
import logging
import traceback

from tornado import gen
from handlers import BaseHandler
from utils import parse_multipart_wrapper
# from tornado.ioloop import IOLoop


@tornado.web.stream_request_body
class UploadHandler(BaseHandler):

    @gen.coroutine
    def prepare(self):
        self.is_multipart = True
        self._insert_async = None
        self._inserted_id = None
        self._uploaded_on = r.now().to_epoch_time()

        # userhash = self.request.headers.get('userhash')
        # self._current_user = self.authenticate(userhash)
        # if not self._current_user:
        #     raise tornado.web.HTTPError(401, "Unauthorized")
        #
        # logging.info('debug current_user')
        # logging.info(self._current_user)
        self._insert_async = (yield self.uploads.insert(dict(
            # user_name=self._current_user.get("user_name"),
            # userid=self._current_user.get("id"),
            uploaded_on=self._uploaded_on
        )).run())

        logging.info('debuggin self._insert_async')
        logging.info(self._insert_async)
        if self._insert_async:
            self._inserted_id = self._insert_async.get("generated_keys")[0]
        self._path_to_upload = os.path.abspath("./uploads")
        self._original_file_name = self.request.headers.get("X-File-Name")
        tmp_content_length = self.request.headers.get("Content-Length")
        self._extension = self.request.headers.get("custom-type")
        logging.debug("self.request.headers: custom-type")
        logging.debug(self._extension)
        if (not self._original_file_name) & (not tmp_content_length):
            self.is_multipart = False
        else:
            if self._original_file_name:
                tmp_ext = os.path.splitext(self._original_file_name)[-1]
                self._extension = tmp_ext.strip(".")
        if self._extension:
            self._file_name = "%s.%s" % (
                self._inserted_id,
                self._extension)
        else:
            self._file_name = self._inserted_id
        self._full_path = os.path.join(self._path_to_upload, self._file_name)
        logging.debug("UPLOAD: FULL PATH")
        logging.debug(self._full_path)
        self._web_url = os.path.join("/contents/uploads/", self._file_name)
        logging.debug("UPLOAD: WEB URL")
        logging.debug(self._web_url)
        self._writer = tempfile.NamedTemporaryFile(mode="w",
                                                   prefix="pb_",
                                                   delete=False)
        if self._inserted_id:
            (yield self.uploads.get(self._inserted_id).update(dict(
                full_path=self._full_path,
                web_url=self._web_url)).run())

    @gen.coroutine
    def post(self):
        if not self._writer.closed:
            self._writer.close()
        # no need to move, just testing.
        # shutil.copyfile(self._writer.name, self._full_path)
        # debug
        logging.info('[Upload Headers]')
        logging.info(self.request.headers)
        parse_multipart_wrapper(self._writer.name,
                                self._full_path,
                                self.is_multipart,
                                self._extension)
        response_str = dict(status="success",
                            file_name=self._file_name,
                            original_name=self._original_file_name,
                            web_url=self._web_url)
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps(response_str))

    @gen.coroutine
    def data_received(self, data):
        if data:
            self._writer.write(data)


class UploadRemover(BaseHandler):

    @gen.coroutine
    def post(self):
        fileid = self.get_argument("fileid")
        print fileid
        condition = {'id': fileid}
        row = yield self.uploads.filter(condition).order_by('id').run(self.conn)
        if row:
            result = yield self.uploads.filter(condition).delete().run(self.conn)
            try:
                os.remove(row[0].get("full_path"))
                os.remove("%s.meta" % (row[0].get("full_path")))
            except:
                print traceback.format_exc()
                pass
        response_str = dict(status="success")
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps(response_str))

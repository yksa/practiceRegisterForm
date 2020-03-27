import mmap
import json
import base64
import rethinkdb as r
import logging
from collections import defaultdict
from collections import deque

CRLF = "\r\n"


def setup_db(db_name="rechat", tables=['events']):
    connection = r.connect(host="localhost")
    try:
        r.db_create(db_name).run(connection)
    except r.RqlRuntimeError:
        logging.warn("Database Exist")

    for tbl in tables:
        try:
            r.db(db_name).table_create(
                tbl, durability="soft").run(connection)
            r.db(db_name).table(tbl).index_create("stamp").run(connection)
        except r.RqlRuntimeError:
            logging.warn('Table already exists.')
        try:
            r.db(db_name).table(tbl).index_create("geolocation").run(
                connection,
                geo=True
            )
            logging.info("Indexed: geolocation: %s" % tbl)
        except:
            logging.warn("Already indexed: geolocation: %s" % tbl)
    logging.info('Database setup completed.')
    connection.close()


def extension_by_meta_for_recording(meta):
    extension = None
    try:
        meta_type = meta.get("data").split("/")
        extension = meta_type[1]
    except:
        pass
    return extension


def valueparser_header(value):
    paired = dict()
    for each in value.split(";"):
        splitted = each.split("=")
        if len(splitted) > 1:
            try:
                # trim spaces
                value = splitted[1].strip()
                # clear quotes
                value = value.strip('"').strip("'")
                paired[splitted[0].strip()] = value
            except:
                pass
    return paired


def parse_header(blockstr):
    """
    Parse multipart/form-data header.

    Args:
        str: blockstr

    Return:
        dict: parsed data (key, value)
    """

    header = dict()
    for each in blockstr.split(CRLF):
        if each:
            if each.startswith("--"):
                header['startboundry'] = each
                continue
            try:
                key, value = each.split(":")
            except:
                logging.debug("DEBUG parse_header")
                logging.debug(each)
            try:
                key = key.strip()
            except:
                continue
            try:
                value = value.strip()
            except:
                continue
            header[key] = value
            parsed = valueparser_header(value)
            if parsed:
                header['%s-Detail' % key] = parsed
    return header


def parse_footer(blockstr):
    """
    Parse multipart/form-data footer.

    Args:
        str: blockstr

    Return:
        dict: parsed data (key, value)
    """
    footer = dict()
    for each in blockstr.split(CRLF):
        if each:
            if each.endswith("--"):
                footer['endboundry'] = each
            else:
                continue
    return footer


def parse_header_footer(blockstr):
    if blockstr is not None:
        if blockstr.startswith("--") and not blockstr.endswith(CRLF):
            return parse_header(blockstr)
        elif blockstr.endswith("--%s" % CRLF):
            return parse_footer(blockstr)


def dump_non_multipart_data(dest, ismultipart):
    if not ismultipart:
        decoded = None
        with open(dest, "r") as tmpf, \
                open("%s.meta" % dest, 'w') as jf:
            tmp_data = tmpf.read()
            splitted = tmp_data.split(",")
            decoded = base64.decodestring(splitted[-1])
            logging.info(splitted[0])
            tmp_meta = splitted[0].split(";")[0].split(":")
            logging.info(tmp_meta)
            try:
                meta = {tmp_meta[0]: tmp_meta[1]}
                json.dump(meta, jf)
            except:
                pass
        if decoded:
            open(dest, "wb").write(decoded)


def parse_multipart_wrapper(source, dest,
                            ismultipart=False,
                            extension=None,
                            start=None,
                            end=None):
    block_size = 1024
    remaining = None
    meta = dict()

    with open(source, "r+b") as fp, \
            open(dest, "wb") as of, \
            open("%s.meta" % dest, 'w') as jf:

        mm = mmap.mmap(fp.fileno(), 0)

        if ismultipart:
            if start is None:
                finder = CRLF * 2
                found = mm.find(finder)
                block = mm.read(found)
                meta.update(parse_header_footer(block))
                start = found + len(finder)

            if end is None:
                finder = '%s--' % CRLF
                end = mm.rfind(finder)
                mm.seek(end + len(CRLF))
                block = mm.read(-1)
                meta.update(parse_header_footer(block))

        if start is not None:
            mm.seek(start)

        if end is not None:
            remaining = end - (start or 0)

        while True:
            chunk_size = 64 * block_size
            if remaining is not None and remaining < chunk_size:
                chunk_size = remaining
            chunk = mm.read(chunk_size)
            if chunk:
                if remaining is not None:
                    remaining -= len(chunk)
                of.write(chunk)
            else:
                if remaining is not None:
                    logging.info('Is remaining zero? %s' % (remaining == 0))
                break

        mm.close()
        json.dump(meta, jf)
    # currently, do not used base64 encoded data.
    # if extension != "ogg":
    #     dump_non_multipart_data(dest, ismultipart)
    return meta


class Channel(object):

    def __init__(self):
        self.waiters = defaultdict(deque)

    def listen(self, uid=None):
        result = Future()
        self.waiters[uid].append(result)
        logging.info("waiting at topic %s" % uid)
        return result

    def notify(self, uid=None, msg_type=None):
        waiters = self.waiters[uid]
        for future in waiters:
            future.set_result(msg_type)
            self.waiters[uid] = deque()

waiter = Channel()

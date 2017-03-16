from urllib.parse import urlsplit, urlunsplit

import pytest
from scrapy.utils.log import configure_logging
from scrapy.utils.python import to_bytes
from twisted.internet import defer
from twisted.web.resource import Resource


class CollectorPipeline:
    def process_item(self, item, spider):
        if not hasattr(spider, 'collected_items'):
            spider.collected_items = []
        spider.collected_items.append(item)
        return item


# make the module importable without running py.test
try:
    inlineCallbacks = pytest.inlineCallbacks
except AttributeError:
    inlineCallbacks = defer.inlineCallbacks


configure_logging()


def html(content):
    return '<html><head></head><body>{}</body></html>'.format(content)


def text_resource(content):
    class Page(Resource):
        isLeaf = True
        def render_GET(self, request):
            request.setHeader(b'content-type', b'text/html')
            return to_bytes(content)
    return Page


def find_item(path, items, key='url'):
    item, = [item for item in items if get_path(item[key]) == path]
    return item


def paths_set(items):
    return {get_path(item['url']) for item in items}


def get_path(url):
    p = urlsplit(url)
    return urlunsplit(['', '', p.path or '/', p.query, p.fragment])


def test_paths_set():
    assert paths_set([
        {'url': 'https://google.com/foo?query=bar'},
        {'url': 'http://google.com/'},
        ]) == {'/foo?query=bar', '/'}

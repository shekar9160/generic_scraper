import os
import tempfile
from urllib.parse import urlsplit, urlunsplit

from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.web.resource import Resource
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging
from scrapy.utils.python import to_bytes

import undercrawler.settings
from undercrawler.spiders import BaseSpider
from tests.mockserver import MockServer


configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})


class SpiderTestCase(TestCase):
    settings = {}

    def setUp(self):
        settings = Settings()
        settings.setmodule(undercrawler.settings)
        settings.update({
            'DOWNLOAD_DELAY': 0.01,
            'AUTOTHROTTLE_START_DELAY': 0.01,
            })
        settings['ITEM_PIPELINES']['tests.utils.CollectorPipeline'] = 100
        splash_url = os.environ.get('SPLASH_URL')
        if splash_url:
            settings['SPLASH_URL'] = splash_url
        settings.update(self.settings)
        runner = CrawlerRunner(settings)
        self.crawler = runner.create_crawler(BaseSpider)


def html(content):
    return '<html><head></head><body>{}</body></html>'.format(content)


def text_resource(content):
    class Page(Resource):
        isLeaf = True
        def render_GET(self, request):
            request.setHeader(b'content-type', b'text/html')
            return to_bytes(content)
    return Page


SinglePage = text_resource(html('<b>hello</b>'))
SinglePage.__name__ = 'SinglePage'


class Follow(Resource):
    def __init__(self):
        super().__init__()
        self.putChild(b'', text_resource(
            html('<a href="/one">one</a> | <a href="/two">Logout</a>'))())
        self.putChild(b'one', text_resource('one')())
        self.putChild(b'two', text_resource('two')())


class TestBasic(SpiderTestCase):
    settings = {
        'AUTOLOGIN_ENABLED': False,
    }

    @defer.inlineCallbacks
    def test_single(self):
        with MockServer(SinglePage) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 1
        item = spider.collected_items[0]
        assert item['url'] == root_url + '/'
        assert item['extracted_text'] == 'hello'
        assert item['raw_content'] == html('<b>hello</b>')

    @defer.inlineCallbacks
    def test_follow(self):
        with MockServer(Follow) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 3
        spider.collected_items.sort(key=lambda item: item['url'])
        item0 = spider.collected_items[0]
        assert item0['url'] == root_url + '/'
        item1 = spider.collected_items[1]
        assert item1['url'] == root_url + '/one'
        assert item1['raw_content'] == html('one')
        item2 = spider.collected_items[2]
        assert item2['url'] == root_url + '/two'
        assert item2['raw_content'] == html('two')


FILE_CONTENTS = 'ёюя'.encode('cp1251')


class PDFFile(Resource):
    isLeaf = True
    def render_GET(self, request):
        request.setHeader(b'content-type', b'application/pdf')
        return FILE_CONTENTS


class WithFile(Resource):
    def __init__(self):
        super().__init__()
        self.putChild(b'', text_resource(html(
            '<a href="/file.pdf">file</a> '
            '<a href="/forbidden.pdf">forbidden file</a>'
            ))())
        self.putChild(b'file.pdf', PDFFile())
        self.putChild(b'forbidden.pdf', text_resource(FILE_CONTENTS * 2)())


class TestDocuments(SpiderTestCase):
    @property
    def settings(self):
        self.tempdir = tempfile.TemporaryDirectory()
        return  {
            'AUTOLOGIN_ENABLED': False,
            'FILES_STORE': 'file://' + self.tempdir.name,
        }

    @defer.inlineCallbacks
    def test(self):
        with MockServer(WithFile) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 3
        file_item = find_item('/file.pdf', spider.collected_items)
        assert file_item['url'] == file_item['obj_original_url'] == \
            root_url + '/file.pdf'
        with open(file_item['obj_stored_url'], 'rb') as f:
            assert f.read() == FILE_CONTENTS
        assert file_item['content_type'] == 'application/pdf'
        forbidden_item = find_item('/forbidden.pdf', spider.collected_items)
        with open(forbidden_item['obj_stored_url'], 'rb') as f:
            assert f.read() == FILE_CONTENTS * 2


def find_item(substring, items):
    [item] = [item for item in items if substring in item['url']]
    return item


class Search(Resource):
    isLeaf = True
    def render_GET(self, request):
        results = ''
        if b'query' in request.args:
            results = 'You found "{}", congrats!'\
                      .format(request.args[b'query'][0].decode())
        return html(
            '<form action="." class="search">'
            '<label for="search">Search:</label> '
            '<input id="search" name="query" type="text"/> '
            '<input type="submit" value="Search"/>'
            '</form>'
            '{}'
            ''.format(results)).encode()

    def render_POST(self, request):
        return html('You searched for "{}"'.format(request.args['query']))\
               .encode()


class TestCrazyFormSubmitter(SpiderTestCase):
    settings = {
        'AUTOLOGIN_ENABLED': False,
    }
    @defer.inlineCallbacks
    def test(self):
        with MockServer(Search) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url, search_terms=['a', 'b'])
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 3
        assert paths_set(spider.collected_items) == \
               {'/', '/?query=a', '/?query=b'}


def paths_set(items):
    _paths_set = set()
    for item in items:
        p = urlsplit(item['url'])
        _paths_set.add(urlunsplit(['', '', p.path, p.query, p.fragment]))
    return _paths_set


def test_paths_set():
    assert paths_set([
        {'url': 'https://google.com/foo?query=bar'},
        {'url': 'http://google.com/'},
        ]) == {'/foo?query=bar', '/'}

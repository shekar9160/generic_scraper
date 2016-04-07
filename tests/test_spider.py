import os, tempfile

from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.web.resource import Resource
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging

import undercrawler.settings
from undercrawler.spiders import BaseSpider
from tests.mockserver import MockServer


configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})


class SpiderTestCase(TestCase):
    settings = {}

    def setUp(self):
        settings = Settings()
        settings.setmodule(undercrawler.settings)
        settings['DOWNLOAD_DELAY'] = 0.1
        settings['ITEM_PIPELINES']['tests.utils.CollectorPipeline'] = 100
        splash_url = os.environ.get('SPLASH_URL')
        if splash_url:
            settings['SPLASH_URL'] = splash_url
        settings.update(self.settings)
        runner = CrawlerRunner(settings)
        self.crawler = runner.create_crawler(BaseSpider)


def html(content):
    return '<html><head></head><body>{}</body></html>'.format(content)


def text_resource(content, name=None):
    class Page(Resource):
        isLeaf = True
        def render_GET(self, request):
            return content.encode('utf-8')
    if name:
        Page.__name__ = name
    return Page


SinglePage = text_resource(html('<b>hello</b>'), name='SinglePage')


class Follow(Resource):
    def __init__(self):
        Resource.__init__(self)
        self.putChild(b'', text_resource(
            html('<a href="/one">one</a> | <a href="/two">two</a>'))())
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


class WithFile(Resource):
    def __init__(self):
        Resource.__init__(self)
        self.putChild(b'', text_resource(
            html('<a href="./file.pdf">file</a>'))())
        self.putChild(b'file.pdf', text_resource('pdf file content')())


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
        assert len(spider.collected_items) == 2
        file_item = spider.collected_items[1]
        assert file_item['url'] == file_item['obj_original_url'] == \
            root_url + '/file.pdf'
        with open(file_item['obj_stored_url']) as f:
            assert f.read() == 'pdf file content'

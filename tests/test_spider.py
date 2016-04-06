import os

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
        settings['ITEM_PIPELINES']['tests.utils.CollectorPipeline'] = 100
        splash_url = os.environ.get('SPLASH_URL')
        if splash_url:
            settings['SPLASH_URL'] = splash_url
        settings.update(self.settings)
        self.runner = CrawlerRunner(settings)


BASE_TPL = '<html><head></head><body>{}</body></html>'


class SinglePage(Resource):
    isLeaf = True
    def render_GET(self, request):
        return to_bytes(BASE_TPL.format('<b>hello</b>'))


class TestBasics(SpiderTestCase):
    settings = {
        'AUTOLOGIN_ENABLED': False,
    }

    @defer.inlineCallbacks
    def test_single(self):
        crawler = self.runner.create_crawler(BaseSpider)
        with MockServer(SinglePage) as s:
            root_url = s.root_url
            yield crawler.crawl(url=root_url)
        spider = crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 1
        item = spider.collected_items[0]
        assert item['url'] == root_url + '/'
        assert item['extracted_text'] == 'hello'
        assert item['raw_content'] == BASE_TPL.format('<b>hello</b>')
